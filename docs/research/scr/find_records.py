# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
recs = json.load(open(sys.argv[1], encoding="utf-8"))
pats = sys.argv[2:]
for r in recs:
    t = r["title"].lower()
    if any(p.lower() in t for p in pats):
        print(f"{r['year']} | cit={r['cited']} | {r['doi']} | {r['title']}")
        print("   J:", r["journal"], "| SRC:", r["sources"])
        print("   A:", r["authors"][:160])
        print()
