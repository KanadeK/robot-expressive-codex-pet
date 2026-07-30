#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"

exec "$python_bin" "$script_dir/install.py" \
  --source "${ROBOT_PET_SOURCE:-$project_root/pet}" \
  "$@"
