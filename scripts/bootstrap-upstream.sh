#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:-${UPSTREAM_MODE:-git-submodule}}"
value(){ python3 "$root/scripts/contract-value.py" "$1"; }
upstream="$(value primary_upstream)"
git_url="$(value git.url)"
vendor_path="$(value git.path)"
zed_package="$(value zed.package)"
if [[ -n "${GH_TOKEN:-}" ]]; then
  git config --global url."https://x-access-token:${GH_TOKEN}@github.com/".insteadOf "https://github.com/"
fi
case "$mode" in
  git-submodule)
    [[ -n "$upstream" && -n "$git_url" ]] || { echo "blocked: no materialized upstream" >&2; exit 78; }
    cd "$root"
    if [[ -f "$vendor_path/.git" || -d "$vendor_path/.git" ]]; then
      git submodule update --init --recursive "$vendor_path"
    else
      mkdir -p "$(dirname "$vendor_path")"
      git submodule add --force "$git_url" "$vendor_path"
      git submodule update --init --recursive "$vendor_path"
    fi
    ;;
  git-clone)
    [[ -n "$upstream" && -n "$git_url" ]] || { echo "blocked: no materialized upstream" >&2; exit 78; }
    rm -rf "$root/$vendor_path"; mkdir -p "$(dirname "$root/$vendor_path")"
    git clone --depth=1 --recurse-submodules "$git_url" "$root/$vendor_path"
    ;;
  zed)
    command -v zed >/dev/null || { echo "blocked: zed CLI unavailable" >&2; exit 78; }
    [[ -n "$zed_package" ]] || { echo "blocked: no published Zed coordinate declared" >&2; exit 78; }
    cd "$root"; zed install
    ;;
  native-package) exec "$root/scripts/native-install.sh" ;;
  *) echo "usage: $0 {git-submodule|git-clone|zed|native-package}" >&2; exit 64 ;;
esac
