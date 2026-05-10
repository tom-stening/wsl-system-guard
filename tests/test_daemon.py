from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from wsl_system_guard.daemon import WSLSystemGuard


class GuardSmokeTests(unittest.TestCase):
    def test_runs_once_and_writes_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scan_root = tmp_path / "repos"
            repo = scan_root / "demo"
            (repo / ".git").mkdir(parents=True)

            config_path = tmp_path / "config.json"
            state_dir = tmp_path / "state"

            config = {
                "scan_roots": [str(scan_root)],
                "exclude_dir_names": [".cache", ".venv", "node_modules"],
                "max_scan_depth": 4,
                "poll_interval_s": 1,
                "repo_refresh_interval_s": 1,
                "warn_available_mb": 0,
                "critical_available_mb": 0,
                "warn_swap_pct": 101.0,
                "critical_swap_pct": 101.0,
                "repo_action_timeout_s": 1,
                "event_cooldown_s": 1,
            }
            config_path.write_text(json.dumps(config), encoding="utf-8")

            guard = WSLSystemGuard(config_path=config_path, state_dir=state_dir, once=True)
            exit_code = guard.run()

            self.assertEqual(exit_code, 0)
            self.assertTrue((state_dir / "current_state.json").exists())

            payload = json.loads((state_dir / "current_state.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["repo_count"], 1)
            self.assertEqual(payload["level"], "normal")


if __name__ == "__main__":
    unittest.main()
