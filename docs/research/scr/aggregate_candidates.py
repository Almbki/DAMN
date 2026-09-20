# -*- coding: utf-8 -*-
"""Aggregate readable .txt candidate files in an api/ dir into one deduped candidate list."""
import json
import os
import re
import sys


def parse_blocks(text):
    blocks = []
    cur = None
    for line in text.splitlines():
        if line.startswith("### ["):
            if cur:
                blocks.append(cur)
            cur = {"title": line.split("]", 1)[1].strip(), "raw": [line]}
        elif cur is not None:
            cur["raw"].append(line)
            if line.startswith("YEAR="):
                for part in line.split("|"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        cur[k.strip()] = v.strip()
            elif line.startswith("DOI="):
                cur.setdefault("DOI", line[4:].strip())
            elif line.startswith("JOURNAL:"):
                cur["journal"] = line[8:].strip()
            elif line.startswith("AUTHORS:"):
                cur["authors"] = line[8:].strip()
            elif line.startswith("ABSTRACT:"):
                cur["abstract"] = line[9:].strip()
    if cur:
        blocks.append(cur)
    return blocks


def norm_doi(d):
    if not d:
        return ""
    d = d.strip().lower()
    d = d.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
    return d


def norm_title(t):
    t = re.sub(r"\s+", " ", (t or "").lower())
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff ]", "", t)
    return t[:80]


def main(api_dir, out_json, out_txt):
    seen = {}
    for name in sorted(os.listdir(api_dir)):
        if not name.endswith(".txt") or name.startswith(("candidates", "pick", "aggregate")):
            continue
        src = name[:-4]
        with open(os.path.join(api_dir, name), encoding="utf-8") as f:
            text = f.read()
        for b in parse_blocks(text):
            if not b.get("title"):
                continue
            doi = norm_doi(b.get("YEAR=", "") or b.get("DOI", ""))
            # DOI is parsed from YEAR line where key is DOI
            doi = norm_doi(b.get("DOI", ""))
            key = norm_doi(doi) or norm_title(b["title"])
            rec = seen.get(key)
            if rec is None:
                rec = {
                    "title": b["title"],
                    "year": b.get("YEAR", ""),
                    "cited": _int(b.get("CITED")),
                    "doi": doi,
                    "journal": b.get("journal", ""),
                    "authors": b.get("authors", ""),
                    "abstract": b.get("abstract", ""),
                    "sources": [],
                    "openalex": b.get("ID", "") if "openalex.org" in b.get("ID", "") else "",
                }
                seen[key] = rec
            if src not in rec["sources"]:
                rec["sources"].append(src)
            if not rec.get("abstract") and b.get("abstract"):
                rec["abstract"] = b["abstract"]
    recs = list(seen.values())
    recs.sort(key=lambda r: (r["cited"], r["year"]), reverse=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(recs, f, ensure_ascii=False, indent=1)
    with open(out_txt, "w", encoding="utf-8") as f:
        for i, r in enumerate(recs, 1):
            f.write(
                f"[{i}] {r['title']}\n"
                f"   YEAR={r['year']} CITED={r['cited']} DOI={r['doi']} SRC={','.join(r['sources'])}\n"
                f"   JOURNAL={r['journal']}\n"
                f"   AUTHORS={r['authors']}\n"
                f"   ABS={r['abstract'][:600]}\n\n"
            )
    print(f"{api_dir}: {len(recs)} unique candidates -> {out_txt}")
    return recs


def _int(v):
    try:
        return int(v)
    except Exception:
        return 0


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
