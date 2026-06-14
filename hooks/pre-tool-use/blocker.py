#!/usr/bin/env python3
"""
Claude Code pre-tool-use hook: blocks destructive bash commands.

Install: ln -sf "$PWD/blocker.py" ~/.claude/hooks/pre-tool-use
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

LOG_FILE = os.path.expanduser("~/.claude/hooks/blocked.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

DESTRUCTIVE_PATTERNS = [
    # rm -rf with path
    (re.compile(r'\brm\s+(-rf?|--recursive\s+--force)\s+'), "Recursive force delete"),
    # DROP TABLE / DROP DATABASE
    (re.compile(r'\bDROP\s+(TABLE|DATABASE|SCHEMA)\b', re.IGNORECASE), "Database DROP statement"),
    # git push --force
    (re.compile(r'\bgit\s+push\s+.*--force\b'), "Force push to git"),
    # TRUNCATE
    (re.compile(r'\bTRUNCATE\s+', re.IGNORECASE), "TRUNCATE statement"),
    # DELETE FROM without WHERE
    (re.compile(r'\bDELETE\s+FROM\b(?!.*\bWHERE\b)', re.IGNORECASE), "DELETE without WHERE clause"),
    # ALTER TABLE DROP
    (re.compile(r'\bALTER\s+TABLE.*DROP\b', re.IGNORECASE), "ALTER TABLE DROP"),
    # Format disk
    (re.compile(r'\bmkfs\.?\b'), "Format filesystem"),
    # Chmod -R 000 or 777 on sensitive dirs
    (re.compile(r'\bchmod\s+-R\s+0{3,4}\s+/'), "Chmod entire filesystem"),
]

# Commands that are SAFE (overrides the above patterns)
SAFE_OVERRIDES = [
    re.compile(r'\brm\s+(-rf?|--recursive\s+--force)\s+(\./|\.\s)'),  # rm -rf ./node_modules etc.
    re.compile(r'\bDROP\s+TABLE\s+IF\s+EXISTS\b'),  # In migrations with IF EXISTS
    re.compile(r'\bDELETE\s+FROM\s+\w+\s+WHERE\b'),  # DELETE with WHERE clause
    re.compile(r'\bgit\s+push\s+--force-with-lease\b'),  # Safer force push variant
]


def log_blocked(command: str, reason: str, project_path: str) -> None:
    entry = {
        "timestamp": datetime.now(tz=datetime.utc).isoformat(),
        "command": command[:500],
        "reason": reason,
        "project_path": project_path,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def check_command(command: str, project_path: str) -> bool:
    """Returns True if the command should be BLOCKED."""

    # Check safe overrides first
    for pattern in SAFE_OVERRIDES:
        if pattern.search(command):
            return False  # Explicitly allowed

    # Check destructive patterns
    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            log_blocked(command, reason, project_path)
            print(
                f"[BLOCKED] {reason}\n"
                f"  Command: {command[:200]}\n"
                f"  Reason: {reason}\n"
                f"  Logged to: {LOG_FILE}\n"
                f"  To allow: use --force-with-lease instead of --force, "
                f"or add an override pattern.",
                file=sys.stderr,
            )
            return True

    return False


def main() -> None:
    input_data = json.loads(sys.stdin.read())

    tool_use = input_data.get("toolUse", {})
    tool_name = tool_use.get("name", "")

    if tool_name != "bash":
        # Not a bash command — let it through
        print(json.dumps({"blocked": False}))
        return

    command = ""
    for item in tool_use.get("input", []):
        if isinstance(item, dict) and "command" in item:
            command = item["command"]
            break

    if isinstance(tool_use.get("input"), dict):
        command = tool_use["input"].get("command", "")

    project_path = os.getcwd()

    blocked = check_command(command, project_path)
    print(json.dumps({"blocked": blocked}))


if __name__ == "__main__":
    main()
