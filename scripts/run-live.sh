#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$root/artifacts"
python3 "$root/scripts/readiness.py" --strict
python3 "$root/scripts/scenario-runner.py"
