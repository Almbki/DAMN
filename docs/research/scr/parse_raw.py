# 解析 OpenAlex raw JSON -> 可读文本（大小写敏感键 + null 安全）
import json
import os
import sys


def conv_abstract(inv):
    if not isinstance(inv, dict):
        return ""
    words = {}
    for word, positions in inv.items():
        for pos in positions:
            words[int(pos)] = word
    if not words:
        return ""
    return " ".join(words[k] for k in sorted(words))


def parse_dir(d):
    report = []
    for name in sorted(os.listdir(d)):
        if not name.startswith("raw_") or not name.endswith(".json"):
            continue
        key = name[4:-5]
        path = os.path.join(d, name)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if "results" not in data:
            report.append(f"{key}: RAW_ERROR keys={list(data.keys())}")
            continue
        results = data.get("results") or []
        blocks = []
        n = 0
        for el in results:
            title = el.get("title") or ""
            if not title:
                continue
            n += 1
            lines = [f"### [{n}] {title}"]
            year = el.get("publication_year")
            cited = el.get("cited_by_count")
            doi = (el.get("doi") or "").replace("https://doi.org/", "")
            lines.append(
                f"YEAR={year}|CITED={cited}|LANG={el.get('language')}|TYPE={el.get('type')}"
                f"|DOI={doi}|ID={el.get('id')}"
            )
            pl = el.get("primary_location") or {}
            src = pl.get("source") or {}
            journal = src.get("display_name") or ""
            b = el.get("biblio") or {}
            lines.append(
                f"JOURNAL: {journal} | VOL={b.get('volume')} ISSUE={b.get('issue')}"
                f" PAGES={b.get('first_page')}-{b.get('last_page')}"
            )
            auths = [a.get("author", {}).get("display_name", "") for a in (el.get("authorships") or [])]
            lines.append(f"AUTHORS: {'; '.join(a for a in auths if a)}")
            abstract = conv_abstract(el.get("abstract_inverted_index"))
            if len(abstract) > 1800:
                abstract = abstract[:1800]
            lines.append(f"ABSTRACT: {abstract}")
            blocks.append("\n".join(lines))
        with open(os.path.join(d, key + ".txt"), "w", encoding="utf-8") as f:
            f.write("\n\n".join(blocks) + "\n")
        report.append(f"{key}: {n}")
    return report


if __name__ == "__main__":
    for d in sys.argv[1:]:
        print(f"{d} ->")
        for r in parse_dir(d):
            print("  " + r)