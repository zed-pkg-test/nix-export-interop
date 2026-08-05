from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    return yaml.safe_load((ROOT / name).read_text())

def test_plan_is_complete():
    plan = load("test-plan.yaml")
    assert plan["schema_version"] == 1
    assert plan["repository"] == ROOT.name
    assert len(plan["objectives"]) >= 3
    assert len(plan["cases"]) == len(plan["objectives"])
    assert len({case["id"] for case in plan["cases"]}) == len(plan["cases"])
    assert re.fullmatch(r"[0-9]+ [0-9]+ [0-9*,-]+ [0-9*,-]+ [0-9*,-]+", plan["schedule_utc"])

def test_dependency_contract_is_explicit():
    dep = load("dependency-contract.yaml")
    assert dep["schema_version"] == 1
    assert set(dep["supported_modes"]) == {"git-submodule", "zed", "native-package"}
    assert dep["readiness"] in {"ready", "mixed", "planned_dependency"}
    for full_name in dep["upstream_repositories"]:
        assert re.fullmatch(r"[^/]+/[^/]+", full_name)
    if dep["readiness"] == "planned_dependency":
        assert dep["planned_upstream_repositories"]

def test_generated_policy_files_exist():
    expected = [
        ".managed-by-test-org-factory",".zpkg.toml","README.md","test-plan.yaml",
        "dependency-contract.yaml","scripts/readiness.py","scripts/bootstrap-upstream.sh",
        "scripts/run-live.sh",".github/workflows/ci.yml",".github/workflows/live.yml",
    ]
    for rel in expected:
        assert (ROOT / rel).exists(), rel
