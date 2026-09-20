# -*- coding: utf-8 -*-
"""Generate GB/T 7714-style citation drafts from verified Crossref records."""
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")


def cite(d):
    auths = d["authors"]
    if len(auths) > 3:
        a = ", ".join(auths[:3]) + ", et al"
    else:
        a = ", ".join(auths)
    t = d["title"].rstrip(".")
    yr = d["year"]
    vol = d["volume"]
    iss = d["issue"]
    pg = d["pages"]
    jour = d["journal"]
    typ = d["type"]
    if typ in ("book-chapter",):
        loc = f"[M]//{jour}. Cambridge: Cambridge University Press, {yr}"
    elif typ in ("proceedings-article",):
        loc = f"[C]//{jour}. {yr}"
    elif typ in ("posted-content",):
        loc = f"[R/OL]. {jour or 'Preprint'}, {yr}"
    else:
        loc = f"[J]. {jour}, {yr}"
    vi = ""
    if vol:
        vi = f", {vol}"
        if iss:
            vi += f"({iss})"
    pgstr = f": {pg}" if pg else ""
    doi = d["doi"]
    return f"{a}. {t}{loc}{vi}{pgstr}. DOI:{doi}."


if __name__ == "__main__":
    d = sys.argv[1]
    recs = []
    for f in sorted(glob.glob(os.path.join(d, "api", "verify", "*.json"))):
        r = json.load(open(f, encoding="utf-8"))
        recs.append(r)
    for i, r in enumerate(recs, 1):
        print(f"[{i}] " + cite(r))
