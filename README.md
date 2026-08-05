# nix-export-interop

    Independent **package-manager** harness in `zed-pkg-test` for `zed-pkg`.

    **Readiness:** `ready`  
    **Primary dependency strategy:** `matrix`  
    **Scheduled cadence:** `17 5 * * *` UTC  
    **Live infrastructure:** Nix

    ## Upstream repositories

    - `zed-pkg/zed-cli`
- `zed-pkg/zed-interfaces`

    ## Acceptance objectives

    1. Verify deterministic Zed-to-Nix export, immutable hashes, and repeatable offline builds across the supported happy-path states and canonical fixtures.
2. Verify deterministic Zed-to-Nix export, immutable hashes, and repeatable offline builds under retries, interruption, concurrency, offline operation, or partial failure.
3. Verify deterministic Zed-to-Nix export, immutable hashes, and repeatable offline builds preserves authorization, idempotency, integrity, observability, and actionable failure classification.

    ## Dependency paths

    This repository tests the upstream through independent installation paths:

    1. `./scripts/bootstrap-upstream.sh git-submodule`
    2. `./scripts/bootstrap-upstream.sh zed`
    3. `./scripts/bootstrap-upstream.sh native-package`

    The publisher materializes a real Git submodule when authenticated access is available. Zed and native package coordinates are recorded in `dependency-contract.yaml`; missing unpublished packages are reported as blocked readiness rather than silently skipped.

    ## Check tiers

    ```bash
    python3 -m pip install -e '.[test]'
    pytest -q
    ./scripts/readiness.py --offline
    ./scripts/run-live.sh
    ```

    Pull requests validate the harness and deterministic contract fixtures. Secret-, service-, emulator-, desktop-, database-, provider-, chaos-, scale-, and soak-dependent checks run by schedule or manual dispatch.

    A live result must be classified as one of:

    - **product regression** — a behavioral invariant fails after dependencies are ready;
    - **blocked dependency** — an upstream, credential, package, emulator, provider sandbox, or deployment is unavailable;
    - **harness regression** — generated metadata, fixtures, workflow, or runner setup is invalid.

    Managed by `github-test-org-factory/1.0.0`.
