#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

INSTALL_BIN_DIR="${HOME}/.local/bin"
CONFIG_DIR="${HOME}/.config/wsl-system-guard"
STATE_DIR="${HOME}/.local/state/wsl-system-guard"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

GUARD_BIN="${INSTALL_BIN_DIR}/wsl-system-guard"
CONFIG_PATH="${CONFIG_DIR}/config.json"
SERVICE_PATH="${SYSTEMD_USER_DIR}/wsl-system-guard.service"
SERVICE_TEMPLATE="${PROJECT_ROOT}/systemd/wsl-system-guard.service.template"

mkdir -p "${INSTALL_BIN_DIR}" "${CONFIG_DIR}" "${STATE_DIR}" "${SYSTEMD_USER_DIR}"

python3 -m pip install --user --upgrade "${PROJECT_ROOT}"

PYTHON_BIN="$(command -v python3)"
cat > "${GUARD_BIN}" <<EOF
#!/usr/bin/env bash
exec "${PYTHON_BIN}" -m wsl_system_guard.daemon "\$@"
EOF
chmod +x "${GUARD_BIN}"

if [[ ! -f "${CONFIG_PATH}" ]]; then
  cat > "${CONFIG_PATH}" <<'JSON'
{
  "scan_roots": [
    "~/code",
    "~/src",
    "~/projects"
  ],
  "exclude_dir_names": [
    ".cache",
    ".local",
    ".venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache"
  ],
  "max_scan_depth": 6,
  "poll_interval_s": 15,
  "repo_refresh_interval_s": 300,
  "warn_available_mb": 2048,
  "critical_available_mb": 1024,
  "warn_swap_pct": 50.0,
  "critical_swap_pct": 70.0,
  "repo_action_timeout_s": 15,
  "event_cooldown_s": 120
}
JSON
fi

sed \
  -e "s|{{GUARD_BIN}}|${GUARD_BIN}|g" \
  -e "s|{{CONFIG_PATH}}|${CONFIG_PATH}|g" \
  -e "s|{{STATE_DIR}}|${STATE_DIR}|g" \
  "${SERVICE_TEMPLATE}" > "${SERVICE_PATH}"

systemctl --user daemon-reload
systemctl --user enable --now wsl-system-guard.service

echo "Installed: ${GUARD_BIN}"
echo "Config: ${CONFIG_PATH}"
echo "State: ${STATE_DIR}"
echo "Service: ${SERVICE_PATH}"
