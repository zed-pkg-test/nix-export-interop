#!/usr/bin/env python3
import sys, yaml
from pathlib import Path
root=Path(__file__).resolve().parents[1]
data=yaml.safe_load((root/"dependency-contract.yaml").read_text())
value=data
for part in sys.argv[1].split("."):
    value=value.get(part) if isinstance(value,dict) else None
print("" if value is None else value)
