# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")


def norm(d):
    return (d or "").strip().lower().replace("https://doi.org/", "")


cand, dois = sys.argv[1], sys.argv[2]
cmap = {norm(r["doi"]): r for r in json.load(open(cand, encoding="utf-8")) if r.get("doi")}
for d in json.load(open(dois, encoding="utf-8")):
    r = cmap.get(norm(d), {})
    oa = r.get("openalex", "")
    print(f"{d} | OA={oa} | SRC={','.join(r.get('sources', []))}")
