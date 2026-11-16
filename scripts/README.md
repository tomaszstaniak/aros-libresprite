# Workflow scripts

Bash only. `env.sh` loads settings: existing environment first, then `../local.env`,
then defaults. Relative values in `local.env` resolve against its directory.

| Script | Purpose |
|---|---|
| `bootstrap.sh [--recreate]` | Create or verify `work/libresprite` |
| `save-patch.sh <name> "<title>" [path ...]` | Save work-copy changes as the next patch |
| `check-reproduction.sh` | Rebuild pin + series in a temporary directory and compare |
| `lib.sh` | Shared helpers |

Keys: `LS_TMP` (temporary directory, default `$TMPDIR` or `/tmp`).
