# macOS Nix daemon readiness certification

This lane independently certifies the workflow-only product repair in
`zed-pkg/zed-cli#251`. The candidate SHA is recorded in
[`canaries/macos-nix-daemon-readiness.json`](../canaries/macos-nix-daemon-readiness.json).

## Exact workflow execution

The test does not maintain a hand-copied approximation of the product logic.
Instead, it checks out the immutable `zed-pkg/zed-cli` commit, locates the
unique step named:

```text
Wait for the Nix store to become ready
```

extracts that step's literal `run: |` shell block, validates the required
bounded retry and diagnostics fragments, checks the extracted shell syntax, and
executes those exact bytes after installing Nix with the same pinned action and
configuration as the product workflow.

The evidence generator independently extracts the block again and refuses to
publish evidence unless it is byte-identical to the executed script.

## Platform claims

### Ubuntu baseline

The ordinary `nix store ping` path must succeed without assuming a daemon-only
remote. The product repository must then evaluate its locked Nixpkgs input to a
realized `/nix/store` path.

### macOS

The exact product block must:

- avoid direct store-database fallback;
- retry `NIX_REMOTE=daemon nix store ping` at most 20 times;
- boundedly kick `system/org.nixos.nix-daemon` between failed attempts;
- append `NIX_REMOTE=daemon` to the GitHub environment only after a successful
  daemon ping;
- emit launchd and socket diagnostics before failing if readiness never occurs;
  and
- permit the next workflow step to ping the store and evaluate the product's
  locked Nixpkgs input.

## Security and isolation

The test uses only public repositories and repository-scoped read credentials
provided by GitHub Actions checkout. No personal token, cross-organization
secret, cache credential, binary substituter key, or publishing identity is
needed.

The evidence record contains the candidate SHA, runner identity, Nix version,
selected remote, locked Nixpkgs store path, product workflow digest, extracted
script digest, and pass/fail claims. It contains no environment secrets or
workflow token.

## Deliberate non-claims

This focused canary does not replace the product repository's complete frozen
Nix graph. It does not certify:

- registry construction and package publication;
- recursive fixed-output hash equality;
- artifact-tamper and incorrect-hash canaries;
- complete CLI compilation; or
- permanently damaged Nix installation recovery.

Those remain in the product `nix-interop` workflow and broader test-org Nix
lanes. This test specifically proves that the exact readiness repair runs on the
platform where the race was observed and still preserves the Linux path.
