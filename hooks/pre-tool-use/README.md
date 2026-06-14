# Claude Code Pre-Tool-Use Hook — Destructive Command Blocker

Blocks dangerous bash commands (`rm -rf`, `DROP TABLE`, `git push --force`, etc.)
before they execute.

## Install

```bash
mkdir -p ~/.claude/hooks && ln -sf "$PWD/blocker.py" ~/.claude/hooks/pre-tool-use
```

That's it. The hook activates on Claude Code's next tool use.

## What It Blocks

| Pattern | Example |
|---------|---------|
| Recursive force delete | `rm -rf /` |
| Database DROP | `DROP TABLE users;` |
| Force push | `git push --force` |
| TRUNCATE | `TRUNCATE orders;` |
| DELETE without WHERE | `DELETE FROM users;` |
| ALTER TABLE DROP | `ALTER TABLE projects DROP COLUMN budget;` |
| Format filesystem | `mkfs.ext4 /dev/sda1` |
| Mass permission change | `chmod -R 000 /` |

## What It Allows (Safe Variants)
- `rm -rf ./node_modules` (relative path, inside project)
- `DROP TABLE IF EXISTS` (migration-safe)
- `DELETE FROM x WHERE y` (with WHERE clause)
- `git push --force-with-lease` (saher force push)

## Logs

Blocked commands are logged to `~/.claude/hooks/blocked.log` with:

- Timestamp
- Attempted command
- Reason for block
- Project path

## Customization

Edit the `DESTRUCTIVE_PATTERNS` and `SAFE_OVERRIDES` lists in `blocker.py`
to add or remove patterns.
