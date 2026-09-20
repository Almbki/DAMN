# -*- coding: utf-8 -*-
"""Fetch authoritative Crossref metadata for a list of DOIs and emit a citation digest.

Usage: python verify_dois.py <outdir> <doi1> <doi2> ...
Saves <outdir>/api/verify/<safe>.json and digest_<ts>.txt (appended).
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
UA = "lit-survey/1.0 (mailto:research@example.com)"


def fetch(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def initials(given):
    if not given:
        return ""
    parts = re.split(r"[\s.\-]+", given)
    return " ".join(p[0].upper() + "." for p in parts if p)


def fmt(m):
    t = (m.get("title") or [""])[0]
    ct = (m.get("container-title") or [""])[0]
    auths = []
    for a in m.get("author", []) or []:
        fam = a.get("family", "")
        giv = initials(a.get("given", ""))
        if fam:
            auths.append(f"{fam.upper()} {giv}".strip())
        elif a.get("name"):
            auths.append(a["name"])
    yr = ""
    for k in ("published-print", "published-online", "issued", "created"):
        if k in m and m[k].get("date-parts"):
            yr = m[k]["date-parts"][0][0]
            break
    return {
        "doi": m.get("DOI", ""),
        "type": m.get("type", ""),
        "title": t,
        "journal": ct,
        "year": yr,
        "volume": m.get("volume", ""),
        "issue": m.get("issue", ""),
        "pages": m.get("page", ""),
        "authors": auths,
        "publisher": m.get("publisher", ""),
    }


def main():
    outdir = sys.argv[1]
    twois = sys.argv[2:]
    if len(twois) == 1 and twois[0].endswith(".json"):
        dois = json.load(open(twois[0], encoding="utf-8"))
    else:
        dois = twois
    ver = os.path.join(outdir, "api", "verify")
    os.makedirs(ver, exist_ok=True)
    digest = []
    for doi in dois:
        try:
            m = fetch(doi)
        except Exception as e:
            digest.append(f"FAIL {doi}: {e}")
            print(f"FAIL {doi}: {e}")
            time.sleep(1)
            continue
        d = fmt(m["message"])
        safe = re.sub(r"[^A-Za-z0-9.]+", "_", doi)[:80]
        with open(os.path.join(ver, safe + ".json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        digest.append(
            f"{d['doi']} | {d['year']} | {d['type']} | {d['title']}\n"
            f"    {d['journal']} | v{d['volume']} i{d['issue']} p{d['pages']}\n"
            f"    {'; '.join(d['authors'])}"
        )
        print(digest[-1].splitlines()[0])
        time.sleep(0.6)
    with open(os.path.join(ver, "DIGEST.txt"), "a", encoding="utf-8") as f:
        f.write("\n\n".join(digest) + "\n\n=====\n\n")
    print(f"\nSaved {len(dois)} records to {ver}")


if __name__ == "__main__":
    main()
