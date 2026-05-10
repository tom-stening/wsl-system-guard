#!/usr/bin/env sh
set -eu

level="${1:-normal}"

if [ "$level" = "critical" ]; then
  printf '%s\n' "critical" > .wsl-guard-level
elif [ "$level" = "warning" ]; then
  printf '%s\n' "warning" > .wsl-guard-level
else
  printf '%s\n' "normal" > .wsl-guard-level
fi
