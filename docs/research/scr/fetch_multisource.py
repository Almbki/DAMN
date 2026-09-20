# -*- coding: utf-8 -*-
"""Multi-source literature fetcher: Crossref + Europe PMC + arXiv (+ optional Semantic Scholar).

Usage:
  python fetch_multisource.py <outdir> <queries.json>

queries.json format: [{"k": "key", "q": "query string"}, ...]
Raw JSON saved to <outdir>/api/. Truncated readable text also written.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from xml.etree import ElementTree as ET

UA = "lit-survey/1.0 (mailto:research@example.com)"
MAIL = "research@example.com"


def http_get(url, headers=None, tries=3, timeout=45):
    h = {"User-Agent": UA, "Accept": "application/json, application/xml, text/xml, */*"}
    if headers:
        h.update(headers)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa
            last = e
            time.sleep(3 * (i + 1))
    print(f"      HTTP FAIL {url[:90]} -> {last}")
    return None


def strip_jats(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def authors_from_cr(item):
    out = []
    for a in item.get("author", []) or []:
        name = " ".join(x for x in [a.get("given"), a.get("family")] if x).strip()
        if not name:
            name = a.get("name", "")
        if name:
            out.append(name)
    return out


def _cached(rawfile, txtfile):
    return os.path.exists(rawfile) and os.path.getsize(rawfile) > 50 and os.path.exists(txtfile)


def fetch_crossref(key, q, outdir, rows=25):
    rawpath = os.path.join(outdir, f"crossref_{key}.json")
    if _cached(rawpath, os.path.join(outdir, f"cr_{key}.txt")):
        print(f"      crossref cached")
        return -1
    url = ("https://api.crossref.org/works?" + urllib.parse.urlencode({
        "query.bibliographic": q,
        "rows": rows,
        "mailto": MAIL,
        "select": "DOI,title,author,issued,container-title,abstract,type,is-referenced-by-count,volume,issue,page,URL,subject",
    }))
    raw = http_get(url)
    if raw is None:
        return 0
    path = os.path.join(outdir, f"crossref_{key}.json")
    with open(path, "wb") as f:
        f.write(raw)
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except Exception as e:
        print(f"      CR parse fail {key}: {e}")
        return 0
    items = data.get("message", {}).get("items", [])
    blocks, n = [], 0
    for it in items:
        title = (it.get("title") or [""])[0]
        if not title:
            continue
        n += 1
        yr = ""
        try:
            yr = it["issued"]["date-parts"][0][0]
        except Exception:
            pass
        ct = (it.get("container-title") or [""])[0]
        blocks.append(
            f"### [{n}] {title}\n"
            f"YEAR={yr}|CITED={it.get('is-referenced-by-count')}|TYPE={it.get('type')}|DOI={it.get('DOI')}\n"
            f"JOURNAL: {ct} | VOL={it.get('volume')} ISSUE={it.get('issue')} PAGES={it.get('page')}\n"
            f"AUTHORS: {'; '.join(authors_from_cr(it))}\n"
            f"ABSTRACT: {strip_jats(it.get('abstract'))[:1800]}\n"
        )
    with open(os.path.join(outdir, f"cr_{key}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(blocks) + "\n")
    return n


def fetch_epmc(key, q, outdir, pagesize=25):
    rawpath = os.path.join(outdir, f"epmc_{key}.json")
    if _cached(rawpath, os.path.join(outdir, f"epmc_{key}.txt")):
        print(f"      epmc cached")
        return -1
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode({
        "query": q,
        "format": "json",
        "pageSize": pagesize,
        "resultType": "core",
        "sort": "CITED desc",
    }))
    raw = http_get(url)
    if raw is None:
        return 0
    with open(os.path.join(outdir, f"epmc_{key}.json"), "wb") as f:
        f.write(raw)
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except Exception as e:
        print(f"      EPMC parse fail {key}: {e}")
        return 0
    res = data.get("resultList", {}).get("result", [])
    blocks, n = [], 0
    for it in res:
        title = it.get("title", "")
        if not title:
            continue
        n += 1
        blocks.append(
            f"### [{n}] {title}\n"
            f"YEAR={it.get('pubYear')}|CITED={it.get('citedByCount')}|TYPE={it.get('pubType')}|DOI={it.get('doi')}|PMID={it.get('pmid')}\n"
            f"JOURNAL: {it.get('journalInfo', {}).get('journal', {}).get('title', it.get('journalTitle',''))}"
            f" | VOL={it.get('journalInfo', {}).get('volume')} ISSUE={it.get('journalInfo', {}).get('issue')}"
            f" PAGES={it.get('pageInfo')}\n"
            f"AUTHORS: {it.get('authorString')}\n"
            f"ABSTRACT: {strip_jats(it.get('abstractText'))[:1800]}\n"
        )
    with open(os.path.join(outdir, f"epmc_{key}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(blocks) + "\n")
    return n


def fetch_arxiv(key, q, outdir, maxr=20):
    rawpath = os.path.join(outdir, f"arxiv_{key}.xml")
    if _cached(rawpath, os.path.join(outdir, f"ax_{key}.txt")):
        print(f"      arxiv cached")
        return -1
    url = ("https://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": f"all:{q}",
        "start": 0,
        "max_results": maxr,
        "sortBy": "relevance",
    }))
    raw = http_get(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; lit-survey/1.0; mailto:research@example.com)",
        "Accept": "application/atom+xml, application/xml, text/xml, */*",
    })
    if raw is None:
        return 0
    with open(os.path.join(outdir, f"arxiv_{key}.xml"), "wb") as f:
        f.write(raw)
    try:
        root = ET.fromstring(raw)
    except Exception as e:
        print(f"      arXiv parse fail {key}: {e}")
        return 0
    ns = {"a": "http://www.w3.org/2005/Atom"}
    blocks, n = [], 0
    for e in root.findall("a:entry", ns):
        title = " ".join((e.findtext("a:title", "", ns) or "").split())
        if not title:
            continue
        n += 1
        auths = [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)]
        pub = e.findtext("a:published", "", ns)[:10]
        doi = ""
        for l in e.findall("a:link", ns):
            if l.get("title") == "doi":
                doi = l.get("href")
        blocks.append(
            f"### [{n}] {title}\n"
            f"YEAR={pub}|DOI={doi}|ARXIV={e.findtext('a:id','',ns)}\n"
            f"AUTHORS: {'; '.join(auths)}\n"
            f"ABSTRACT: {' '.join((e.findtext('a:summary','',ns) or '').split())[:1800]}\n"
        )
    with open(os.path.join(outdir, f"ax_{key}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(blocks) + "\n")
    return n


if __name__ == "__main__":
    outdir = sys.argv[1]
    queries = json.load(open(sys.argv[2], encoding="utf-8"))
    api = os.path.join(outdir, "api")
    os.makedirs(api, exist_ok=True)
    t0 = time.time()
    for i, item in enumerate(queries, 1):
        k, q = item["k"], item["q"]
        print(f"== [{i}/{len(queries)}] {k}: {q}", flush=True)
        print("   crossref:", fetch_crossref(k, q, api), flush=True)
        time.sleep(1)
        print("   epmc    :", fetch_epmc(k, q, api), flush=True)
        time.sleep(1)
        if item.get("arxiv"):
            print("   arxiv   :", fetch_arxiv(k, q, api), flush=True)
            time.sleep(3)
    print(f"DONE in {time.time()-t0:.0f}s", flush=True)
