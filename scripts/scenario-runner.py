#!/usr/bin/env python3
import json, os, subprocess
from pathlib import Path
import yaml
root=Path(__file__).resolve().parents[1]
plan=yaml.safe_load((root/"test-plan.yaml").read_text())
cmd=os.getenv("SCENARIO_COMMAND")
if not cmd:
    print("blocked: set SCENARIO_COMMAND to the product-specific black-box command")
    raise SystemExit(78)
result=subprocess.run(["bash","-lc",cmd],cwd=root)
out=root/"artifacts/scenario-result.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({"command":cmd,"exit_code":result.returncode,"repository":plan["repository"]},indent=2)+"\n")
raise SystemExit(result.returncode)
