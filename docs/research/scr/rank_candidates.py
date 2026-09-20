# -*- coding: utf-8 -*-
"""Rank candidates by topical relevance using keyword scoring on title + abstract."""
import json
import re
import sys

# direction -> list of (regex, weight); title match counts double
KEYWORDS = {
    "03": [
        (r"task decompos|goal decompos|decompos\w* (task|goal|problem)", 6),
        (r"hierarchical (task|plan|goal|reinforcement|model)", 6),
        (r"sub-?goal", 6),
        (r"task granularit|granularit\w* (of )?(task|goal|plan)", 6),
        (r"chunk\w*", 4),
        (r"goal setting|goal-setting", 6),
        (r"implementation intention", 6),
        (r"proximal goal|proximal sub-?goal|distal goal", 5),
        (r"goal gradient|gradient hypothesis", 5),
        (r"task analysis|work breakdown|task breakdown", 5),
        (r"goal hierarch|hierarch\w* goal", 5),
        (r"sub-?goal label", 5),
        (r"planning|plan generation", 2),
        (r"task structure|task complexity|task difficulty", 3),
        (r"self-?regulat|goal pursuit|goal commitment", 3),
        (r"goal orientation|mastery goal|performance goal", 3),
        (r"small wins|incremental goal", 4),
        (r"problem decompos|divide and conquer", 4),
        (r"task selection|task assignment|task allocation", 2),
        (r"knowledge tracing|curriculum", 2),
        (r"goal\b", 1),
    ],
    "04": [
        (r"completion time|time to complet|task time|time on task|time-on-task", 6),
        (r"duration predict|predict\w* duration|duration estimation|time predict", 6),
        (r"effort estimation|effort predict|cost estimation", 5),
        (r"planning fallacy", 6),
        (r"productivity|productiv", 4),
        (r"human performance (predict|model)|performance prediction", 5),
        (r"individual difference", 4),
        (r"learning curve|power law of practice|practice\b", 4),
        (r"response time|reaction time", 3),
        (r"performance time|work rate|work pace", 4),
        (r"software effort|software development effort|story point", 5),
        (r"labor productivity|labour productivity", 4),
        (r"skill|expertise|learning rate", 3),
        (r"workload|fatigue|cognitive load", 3),
        (r"schedule|scheduling|duration", 2),
        (r"estimation|estimat|forecast|predict", 2),
        (r"machine learning|neural network|regression model", 2),
        (r"time use|time management|time perception", 3),
        (r"deadline", 3),
        (r"performance", 1),
    ],
}


def score(rec, kws):
    title = rec.get("title", "").lower()
    abs = (rec.get("abstract", "") or "").lower()
    s = 0
    for pat, w in kws:
        if re.search(pat, title):
            s += w * 2
        if re.search(pat, abs):
            s += w
    return s


def main(path, out):
    recs = json.load(open(path, encoding="utf-8"))
    from collections import Counter
    top = Counter((r.get("sources") or ["?"])[0].split("_")[0] for r in recs)
    kws = KEYWORDS["04"] if "04" in out else KEYWORDS["03"]
    for r in recs:
        r["score"] = score(r, kws)
    recs = [r for r in recs if r["score"] >= 8]
    recs.sort(key=lambda r: (r["score"], r["cited"]), reverse=True)
    lines = []
    for i, r in enumerate(recs, 1):
        lines.append(
            f"[{i}] SCORE={r['score']} CITED={r['cited']} YEAR={r['year']} DOI={r['doi']} SRC={','.join(r['sources'])}\n"
            f"    T: {r['title']}\n"
            f"    J: {r['journal']}\n"
            f"    A: {r['authors'][:150]}\n"
            f"    X: {r['abstract'][:420]}\n"
        )
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{path}: {len(recs)} relevant candidates -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
