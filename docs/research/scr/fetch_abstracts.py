# -*- coding: utf-8 -*-
"""Fetch abstracts for a DOI list via Europe PMC, with Semantic Scholar fallback.

Usage: python fetch_abstracts.py <outdir> <dois.json>
Saves <outdir>/api/abstracts.json and prints a readable digest.
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


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if i == tries - 1:
                return {"_error": str(e)}
            time.sleep(3 * (i + 1))


def epmc(doi):
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
        {"query": f'DOI:"{doi}"', "format": "json", "resultType": "core", "pageSize": 1}
    )
    d = get(url)
    try:
        res = d["resultList"]["result"]
        if res:
            return res[0].get("abstractText", "") or ""
    except Exception:
        pass
    return ""


def s2(doi):
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi)}?fields=title,abstract,venue,year,citationCount"
    d = get(url, tries=2)
    if isinstance(d, dict) and d.get("abstract"):
        return d["abstract"]
    return ""


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


if __name__ == "__main__":
    outdir = sys.argv[1]
    dois = json.load(open(sys.argv[2], encoding="utf-8"))
    out = os.path.join(outdir, "api", "abstracts.json")
    existing = {}
    if os.path.exists(out):
        existing = {r["doi"]: r for r in json.load(open(out, encoding="utf-8"))}
    results = list(existing.values())
    for doi in dois:
        if doi in existing and existing[doi].get("abstract"):
            continue
        a = clean(epmc(doi))
        src = "epmc"
        if not a:
            a = clean(s2(doi))
            src = "s2"
            time.sleep(2)
        print(f"{doi} | len={len(a)} | {src}")
        results = [r for r in results if r["doi"] != doi]
        results.append({"doi": doi, "source": src, "abstract": a})
        time.sleep(1)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    for r in results:
        print("\n=== ", r["doi"], f"({r['source']}, {len(r['abstract'])} chars)")
        print(r["abstract"][:1500])
