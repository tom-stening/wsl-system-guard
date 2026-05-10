from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = {
    "scan_roots": ["~/code", "~/src", "~/projects"],
    "exclude_dir_names": [
        ".cache",
        ".local",
        ".venv",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
    ],
    "max_scan_depth": 6,
    "poll_interval_s": 15,
    "repo_refresh_interval_s": 300,
    "warn_available_mb": 2048,
    "critical_available_mb": 1024,
    "warn_swap_pct": 50.0,
    "critical_swap_pct": 70.0,
    "repo_action_timeout_s": 15,
    "event_cooldown_s": 120,
}


@dataclass
class MemoryState:
    total_mb: int
    available_mb: int
    used_mb: int
    percent_used: float
    swap_total_mb: int
    swap_used_mb: int
    swap_percent_used: float


class WSLSystemGuard:
    def __init__(self, config_path: Path, state_dir: Path, once: bool = False):
        self.config_path = config_path
        self.state_dir = state_dir
        self.once = once
        self.stop_requested = False
        self.last_event_by_repo: dict[str, float] = {}
        self.cached_repos: list[Path] = []
        self.last_repo_refresh = 0.0

        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.state_dir / "events.jsonl"
        self.current_state_path = self.state_dir / "current_state.json"

        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8"
            )
            return dict(DEFAULT_CONFIG)

        loaded = json.loads(self.config_path.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_CONFIG)
        merged.update(loaded)
        return merged

    def _read_meminfo(self) -> dict[str, int]:
        fields: dict[str, int] = {}
        with Path("/proc/meminfo").open("r", encoding="utf-8") as handle:
            for line in handle:
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                number = value.strip().split()[0]
                fields[key] = int(number)
        return fields

    def _memory_state(self) -> MemoryState:
        info = self._read_meminfo()
        total_kb = info.get("MemTotal", 0)
        avail_kb = info.get("MemAvailable", info.get("MemFree", 0))
        used_kb = max(total_kb - avail_kb, 0)
        swap_total_kb = info.get("SwapTotal", 0)
        swap_free_kb = info.get("SwapFree", 0)
        swap_used_kb = max(swap_total_kb - swap_free_kb, 0)

        mem_pct = (used_kb / total_kb * 100.0) if total_kb else 0.0
        swap_pct = (swap_used_kb / swap_total_kb * 100.0) if swap_total_kb else 0.0

        return MemoryState(
            total_mb=int(total_kb / 1024),
            available_mb=int(avail_kb / 1024),
            used_mb=int(used_kb / 1024),
            percent_used=round(mem_pct, 2),
            swap_total_mb=int(swap_total_kb / 1024),
            swap_used_mb=int(swap_used_kb / 1024),
            swap_percent_used=round(swap_pct, 2),
        )

    def _pressure_level(self, mem: MemoryState) -> str:
        if (
            mem.available_mb <= int(self.config["critical_available_mb"])
            or mem.swap_percent_used >= float(self.config["critical_swap_pct"])
        ):
            return "critical"
        if (
            mem.available_mb <= int(self.config["warn_available_mb"])
            or mem.swap_percent_used >= float(self.config["warn_swap_pct"])
        ):
            return "warning"
        return "normal"

    def _scan_repos(self) -> list[Path]:
        now = time.time()
        refresh_interval = int(self.config["repo_refresh_interval_s"])
        if self.cached_repos and (now - self.last_repo_refresh) < refresh_interval:
            return self.cached_repos

        roots = [Path(p).expanduser() for p in self.config["scan_roots"]]
        exclude_names = set(self.config["exclude_dir_names"])
        max_depth = int(self.config["max_scan_depth"])

        repos: list[Path] = []
        for root in roots:
            if not root.exists() or not root.is_dir():
                continue

            for current_root, dirs, _files in os.walk(root):
                current = Path(current_root)
                depth = len(current.relative_to(root).parts)

                if depth > max_depth:
                    dirs[:] = []
                    continue

                dirs[:] = [d for d in dirs if d not in exclude_names]
                if ".git" in dirs:
                    repos.append(current)
                    dirs[:] = []

        self.cached_repos = sorted(set(repos))
        self.last_repo_refresh = now
        return self.cached_repos

    def _emit_event(self, event: dict[str, Any]) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

        self.current_state_path.write_text(
            json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def _apply_repo_action(self, repo: Path, event: dict[str, Any]) -> None:
        now = time.time()
        cooldown = int(self.config["event_cooldown_s"])
        last = self.last_event_by_repo.get(str(repo), 0.0)
        if (now - last) < cooldown:
            return

        repo_event = dict(event)
        repo_event["repo"] = str(repo)
        repo_event_path = repo / ".git" / "wsl-system-guard-state.json"
        repo_event_path.write_text(
            json.dumps(repo_event, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        action_script = repo / ".wsl-system-guard-action"
        if action_script.exists():
            try:
                timeout_s = int(self.config["repo_action_timeout_s"])
                env = os.environ.copy()
                env["WSL_GUARD_LEVEL"] = str(event["level"])
                env["WSL_GUARD_AVAILABLE_MB"] = str(event["available_mb"])
                env["WSL_GUARD_SWAP_PERCENT"] = str(event["swap_percent"])
                env["WSL_GUARD_EVENT_TIME"] = str(event["timestamp"])
                subprocess.run(
                    ["/bin/sh", str(action_script), str(event["level"])],
                    cwd=str(repo),
                    env=env,
                    timeout=timeout_s,
                    check=False,
                    capture_output=True,
                    text=True,
                )
            except Exception:
                pass

        self.last_event_by_repo[str(repo)] = now

    def run(self) -> int:
        while not self.stop_requested:
            mem = self._memory_state()
            level = self._pressure_level(mem)
            repos = self._scan_repos()

            event = {
                "timestamp": int(time.time()),
                "level": level,
                "total_mb": mem.total_mb,
                "used_mb": mem.used_mb,
                "available_mb": mem.available_mb,
                "memory_percent": mem.percent_used,
                "swap_total_mb": mem.swap_total_mb,
                "swap_used_mb": mem.swap_used_mb,
                "swap_percent": mem.swap_percent_used,
                "repo_count": len(repos),
            }
            self._emit_event(event)

            if level in {"warning", "critical"}:
                for repo in repos:
                    self._apply_repo_action(repo, event)

            if self.once:
                break

            time.sleep(int(self.config["poll_interval_s"]))

        return 0


def _install_signal_handlers(guard: WSLSystemGuard) -> None:
    def _request_stop(_sig: int, _frame: Any) -> None:
        guard.stop_requested = True

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run system-wide WSL guard daemon")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument(
        "--config",
        default="~/.config/wsl-system-guard/config.json",
        help="Path to config JSON",
    )
    parser.add_argument(
        "--state-dir",
        default="~/.local/state/wsl-system-guard",
        help="Directory for state snapshots and event logs",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    guard = WSLSystemGuard(
        config_path=Path(args.config).expanduser(),
        state_dir=Path(args.state_dir).expanduser(),
        once=args.once,
    )
    _install_signal_handlers(guard)
    return guard.run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
