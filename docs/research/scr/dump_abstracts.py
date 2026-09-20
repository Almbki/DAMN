# -*- coding: utf-8 -*-
"""Merge abstract sources and dump per-DOI digest for selected papers."""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")


def norm(d):
    return (d or "").strip().lower().replace("https://doi.org/", "")


def main(cand, ab, dois, out):
    if isinstance(dois, str):
        dois = json.load(open(dois, encoding="utf-8"))
    cmap = {norm(r["doi"]): r for r in json.load(open(cand, encoding="utf-8")) if r.get("doi")}
    amap = {}
    if os.path.exists(ab):
        amap = {norm(r["doi"]): r for r in json.load(open(ab, encoding="utf-8"))}
    lines = []
    for d in dois:
        c = cmap.get(norm(d), {})
        a = amap.get(norm(d), {})
        abs_txt = (c.get("abstract") or "") or (a.get("abstract") or "")
        lines.append(
            f"### {d}\n"
            f"TITLE: {c.get('title','')}\n"
            f"YEAR: {c.get('year','')} | CITED: {c.get('cited','')} | J: {c.get('journal','')}\n"
            f"AUTHORS: {c.get('authors','')}\n"
            f"ABSTRACT: {re.sub(r'\\s+',' ',abs_txt)[:2600]}\n"
        )
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print(f"wrote {out}: {len(lines)} entries")


if __name__ == "__main__":
    main(*sys.argv[1:])
