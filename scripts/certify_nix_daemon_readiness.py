#!/usr/bin/env python3
"""Extract and certify the exact Nix-store readiness step from zed-cli.

The extractor is intentionally YAML-library independent: it locates the unique
named workflow step and preserves its literal shell block. The live workflow
then executes those exact bytes after installing the same pinned Nix action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

STEP_NAME = "Wait for the Nix store to become ready"
REQUIRED_FRAGMENTS = (
    'if [[ "$RUNNER_OS" != "macOS" ]]; then',
    "nix store ping",
    "for attempt in $(seq 1 20); do",
    "NIX_REMOTE=daemon nix store ping",
    "printf 'NIX_REMOTE=daemon\\n' >> \"$GITHUB_ENV\"",
    "sudo launchctl kickstart -k system/org.nixos.nix-daemon",
    "sudo launchctl print system/org.nixos.nix-daemon || true",
    "ls -la /nix/var/nix/daemon-socket || true",
    'echo "Nix daemon did not become ready" >&2',
)


class CertificationFailure(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        raise CertificationFailure(
            f"command failed ({result.returncode}): {list(command)!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def extract_step(workflow: Path) -> bytes:
    raw = workflow.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    step_indexes = [
        index
        for index, line in enumerate(lines)
        if line.strip() == f"- name: {STEP_NAME}"
    ]
    if len(step_indexes) != 1:
        raise CertificationFailure(
            f"expected exactly one `{STEP_NAME}` step, found {len(step_indexes)}"
        )

    start = step_indexes[0]
    run_index = None
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        indentation = len(lines[index]) - len(lines[index].lstrip(" "))
        if stripped.startswith("- name:") and indentation <= 6:
            break
        if stripped == "run: |":
            run_index = index
            break
    if run_index is None:
        raise CertificationFailure(f"`{STEP_NAME}` has no literal `run: |` block")

    body: list[str] = []
    for line in lines[run_index + 1 :]:
        stripped = line.strip()
        indentation = len(line) - len(line.lstrip(" "))
        if stripped and indentation <= 8:
            break
        if not stripped:
            body.append("\n")
            continue
        if indentation < 10:
            raise CertificationFailure(
                f"unexpected indentation inside readiness block: {line!r}"
            )
        body.append(line[10:])

    script = "".join(body)
    if not script.strip():
        raise CertificationFailure("readiness shell block is empty")
    for fragment in REQUIRED_FRAGMENTS:
        if fragment not in script:
            raise CertificationFailure(
                f"readiness shell block is missing required fragment: {fragment}"
            )
    if script.count("NIX_REMOTE=daemon nix store ping") != 1:
        raise CertificationFailure("daemon ping must appear exactly once in the retry loop")
    if script.count("seq 1 20") != 1:
        raise CertificationFailure("readiness retry bound must be exactly 20 attempts")
    return script.encode("utf-8")


def command_extract(args: argparse.Namespace) -> int:
    workflow = args.workflow.resolve()
    output = args.output.resolve()
    script = extract_step(workflow)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(script)
    print(
        json.dumps(
            {
                "workflow": str(workflow),
                "output": str(output),
                "script_sha256": sha256_bytes(script),
                "bytes": len(script),
            },
            sort_keys=True,
        )
    )
    return 0


def command_evidence(args: argparse.Namespace) -> int:
    candidate = args.candidate.lower()
    if len(candidate) != 40 or any(c not in "0123456789abcdef" for c in candidate):
        raise CertificationFailure("candidate must be a full lowercase 40-hex commit")

    product = args.product.resolve()
    workflow = product / ".github" / "workflows" / "nix-interop.yml"
    extracted = args.extracted.resolve()
    if extract_step(workflow) != extracted.read_bytes():
        raise CertificationFailure("executed readiness script differs from product workflow")

    checked_out = run(["git", "rev-parse", "HEAD"], cwd=product).stdout.strip()
    if checked_out != candidate:
        raise CertificationFailure(
            f"product checkout drift: expected {candidate}, found {checked_out}"
        )

    nix_version = run(["nix", "--version"]).stdout.strip()
    ping = run(["nix", "store", "ping"])
    nixpkgs = run(
        [
            "nix",
            "eval",
            "--raw",
            "./nix#lib.nixpkgsPath",
            "--no-update-lock-file",
        ],
        cwd=product,
    ).stdout.strip()
    if not nixpkgs.startswith("/nix/store/") or not Path(nixpkgs).is_dir():
        raise CertificationFailure(
            f"locked Nixpkgs input is not a realized store path: {nixpkgs!r}"
        )

    remote = os.environ.get("NIX_REMOTE", "")
    runner_os = os.environ.get("RUNNER_OS", "")
    if runner_os == "macOS" and remote != "daemon":
        raise CertificationFailure(
            f"macOS readiness did not export NIX_REMOTE=daemon: {remote!r}"
        )
    if "permission denied" in (ping.stdout + ping.stderr).lower():
        raise CertificationFailure("Nix ping fell back to inaccessible direct-store state")

    evidence = {
        "schema": "zed-pkg-test/macos-nix-daemon-readiness/v1",
        "candidate": candidate,
        "runner": {
            "os": runner_os,
            "arch": os.environ.get("RUNNER_ARCH", ""),
        },
        "nix": {
            "version": nix_version,
            "remote": remote or None,
            "store_ping": "passed",
            "locked_nixpkgs_path": nixpkgs,
        },
        "workflow": {
            "path": ".github/workflows/nix-interop.yml",
            "sha256": sha256_bytes(workflow.read_bytes()),
            "readiness_script_sha256": sha256_bytes(extracted.read_bytes()),
            "readiness_script_matches_product": True,
        },
        "claims": {
            "macos_uses_daemon_after_readiness": runner_os != "macOS" or remote == "daemon",
            "ordinary_store_ping_passed": True,
            "locked_repository_nix_eval_passed": True,
            "direct_store_permission_fallback_observed": False,
        },
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)

    extract = commands.add_parser("extract")
    extract.add_argument("--workflow", required=True, type=Path)
    extract.add_argument("--output", required=True, type=Path)
    extract.set_defaults(handler=command_extract)

    evidence = commands.add_parser("evidence")
    evidence.add_argument("--candidate", required=True)
    evidence.add_argument("--product", required=True, type=Path)
    evidence.add_argument("--extracted", required=True, type=Path)
    evidence.add_argument("--output", required=True, type=Path)
    evidence.set_defaults(handler=command_evidence)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.handler(args)
    except CertificationFailure as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
