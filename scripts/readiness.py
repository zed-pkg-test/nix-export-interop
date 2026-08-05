#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, urllib.error, urllib.request
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def probe(full_name):
    url=f"https://api.github.com/repos/{full_name}"
    headers={"Accept":"application/vnd.github+json","User-Agent":"paired-test-readiness/1"}
    token=os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token: headers["Authorization"]=f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=20) as r:
            return r.status == 200, f"http-{r.status}"
    except urllib.error.HTTPError as e:
        return False, f"http-{e.code}-missing-private-or-forbidden"
    except Exception as e:
        return False, f"network-error:{type(e).__name__}"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--offline",action="store_true")
    ap.add_argument("--strict",action="store_true")
    ap.add_argument("--output",default="artifacts/readiness-status.json")
    args=ap.parse_args()
    dep=yaml.safe_load((ROOT/"dependency-contract.yaml").read_text())
    result={"declared_readiness":dep["readiness"],"overall":"ready","upstreams":[],"credential_hint":None}
    if dep["readiness"]=="planned_dependency":
        result["overall"]="blocked-planned-upstream"
    for name in dep["upstream_repositories"]:
        if args.offline:
            result["upstreams"].append({"repository":name,"status":"not-probed-offline"})
        else:
            ok,reason=probe(name)
            result["upstreams"].append({"repository":name,"status":"reachable" if ok else "blocked","reason":reason})
            if not ok and result["overall"]=="ready":
                result["overall"]="blocked-upstream-or-credentials"
                result["credential_hint"]="Configure CROSS_ORG_APP_ID/CROSS_ORG_APP_PRIVATE_KEY or authenticated Git transport."
    out=ROOT/args.output
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    return 78 if args.strict and result["overall"]!="ready" else 0

if __name__=="__main__":
    raise SystemExit(main())
