# -*- coding: utf-8 -*-
"""Resolve every DOI via doi.org and report HTTP status (HEAD, follow redirects)."""
import json
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
UA = "Mozilla/5.0 (compatible; lit-survey/1.0; mailto:research@example.com)"


def check(doi):
    url = "https://doi.org/" + urllib.parse.quote(doi, safe="")
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, url
    except Exception as e:
        return "ERR", str(e)[:80]


for f in sys.argv[1:]:
    dois = json.load(open(f, encoding="utf-8"))
    bad = 0
    for d in dois:
        st, loc = check(d)
        if st not in (200, 301, 302, 303, 307, 308):
            bad += 1
            print(f"  BAD {st} {d} -> {loc}")
        time.sleep(0.3)
    print(f"{f}: {len(dois)} DOIs, {bad} problems")
