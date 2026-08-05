#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "strategy=matrix language= package="
echo "blocked: add the upstream-specific native consumer command" >&2; exit 78
