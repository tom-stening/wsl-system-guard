# WSL System Guard

WSL System Guard is a host-level daemon that monitors memory and swap pressure
for the whole WSL environment and propagates pressure events to all discovered
git repositories.

## Why this exists

Repo-local crash prevention is helpful but not universal. This daemon runs
outside any single project, so every repo can rely on one neutral monitor.

## Features

- System-wide monitoring from `/proc/meminfo`
- Repository discovery under configured scan roots
- Per-repo state fan-out to `.git/wsl-system-guard-state.json`
- Optional repo hook execution via `.wsl-system-guard-action`
- User-level systemd service support
- Zero runtime dependencies (stdlib only)

## Install

```bash
bash scripts/install.sh
```

Then verify:

```bash
systemctl --user status wsl-system-guard.service
journalctl --user -u wsl-system-guard.service -f
```

## Configuration

Default config path:

```text
~/.config/wsl-system-guard/config.json
```

Important keys:

- `scan_roots`: directories to search for git repositories
- `warn_available_mb`: warning threshold for free memory
- `critical_available_mb`: critical threshold for free memory
- `warn_swap_pct`: warning threshold for swap usage
- `critical_swap_pct`: critical threshold for swap usage

## Repo contract

If a repository has an executable script at `.wsl-system-guard-action`, the guard
will call it on warning and critical events:

```bash
.wsl-system-guard-action <level>
```

Environment variables exposed:

- `WSL_GUARD_LEVEL`
- `WSL_GUARD_AVAILABLE_MB`
- `WSL_GUARD_SWAP_PERCENT`
- `WSL_GUARD_EVENT_TIME`

See `examples/repo-hook.sh`.

## One-shot mode

```bash
python3 -m wsl_system_guard.daemon --once
```

## CI and release

- CI runs on push and pull requests using Python 3.10 to 3.12.
- Tagged releases in the form vX.Y.Z automatically build and publish release artifacts.
