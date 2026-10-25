"""Fit one unidimensional GRM per domain with girth.grm_mml.

Usage:
    python scripts/fit_grm_domains.py --domains E O A C
    python scripts/fit_grm_domains.py --domains N --overwrite

Results are cached as npz files in the temp workspace so a long calibration
can be resumed without refitting completed domains.
"""

from __future__ import annotations

import argparse
import gc
import json
import time
import warnings
from pathlib import Path

import girth
import numpy as np

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
DAT = ROOT / "dataset" / "IPIP120.dat"
MAPPING = ROOT / "artifacts" / "item_mapping.json"
RESULT_DIR = Path(r"C:\Users\ROG\AppData\Local\Temp\opencode\ipip\grm_results")

N_ROWS = 619_150
N_ITEMS = 120
MAX_ITER = 25
QUADRATURE_N = 41
QUADRATURE_BOUNDS = (-4.5, 4.5)


def load_items() -> np.ndarray:
    raw = np.fromfile(DAT, dtype=np.uint8).reshape(-1, 153)
    items = raw[:, 31:151].astype(np.int16) - 48
    del raw
    if items.shape != (N_ROWS, N_ITEMS):
        raise SystemExit(f"unexpected item matrix: {items.shape}")
    if items.min() != 0 or items.max() != 5:
        raise SystemExit(f"unexpected item range: {items.min()}..{items.max()}")
    return items


def load_mapping() -> dict[str, list[dict]]:
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    by_domain: dict[str, list[dict]] = {}
    for item in mapping["items"]:
        by_domain.setdefault(item["domain"], []).append(item)
    for domain, items in by_domain.items():
        items.sort(key=lambda x: x["official_short_id"])
        if len(items) != 24:
            raise SystemExit(f"domain {domain} has {len(items)} items, expected 24")
    return by_domain


def fit_domain(items: np.ndarray, domain_items: list[dict], max_iter: int) -> dict:
    cols = [item["official_short_id"] - 1 for item in domain_items]
    x = items[:, cols].T.astype(np.int32)
    x[x == 0] = girth.INVALID_RESPONSE

    options = {
        "max_iteration": max_iter,
        "quadrature_n": QUADRATURE_N,
        "quadrature_bounds": QUADRATURE_BOUNDS,
        "use_LUT": True,
        "estimate_distribution": False,
    }
    start = time.time()
    result = girth.grm_mml(x, options)
    elapsed = time.time() - start

    a = np.asarray(result["Discrimination"], dtype=float)
    b = np.asarray(result["Difficulty"], dtype=float)
    if a.shape != (24,) or b.shape != (24, 4):
        raise SystemExit(f"unexpected GRM output shape: a={a.shape}, b={b.shape}")
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise SystemExit("GRM returned non-finite parameters")
    return {
        "a": a,
        "b": b,
        "a_min": float(a.min()),
        "a_max": float(a.max()),
        "a_median": float(np.median(a)),
        "threshold_order_ok": bool(np.all(np.diff(b, axis=1) > 0)),
        "elapsed_seconds": elapsed,
        "max_iter": max_iter,
        "n_respondents": int(x.shape[1]),
        "n_items": int(x.shape[0]),
        "aic_final": float(result.get("AIC", {}).get("final", np.nan)),
        "bic_final": float(result.get("BIC", {}).get("final", np.nan)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domains", nargs="+", default=["N", "E", "O", "A", "C"])
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-iter", type=int, default=MAX_ITER)
    args = parser.parse_args()

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    items = load_items()
    by_domain = load_mapping()

    for domain in args.domains:
        if domain not in by_domain:
            raise SystemExit(f"unknown domain: {domain}")
        path = RESULT_DIR / f"grm_{domain}.npz"
        if path.exists() and not args.overwrite:
            print(f"[skip] {domain}: {path.name} exists")
            continue
        print(f"[fit] domain {domain} ({len(by_domain[domain])} items, {items.shape[0]} respondents, max_iter={args.max_iter})", flush=True)
        result = fit_domain(items, by_domain[domain], args.max_iter)
        np.savez(
            path,
            a=result["a"],
            b=result["b"],
            a_min=result["a_min"],
            a_max=result["a_max"],
            a_median=result["a_median"],
            threshold_order_ok=result["threshold_order_ok"],
            elapsed_seconds=result["elapsed_seconds"],
            max_iter=result["max_iter"],
            n_respondents=result["n_respondents"],
            n_items=result["n_items"],
            aic_final=result["aic_final"],
            bic_final=result["bic_final"],
        )
        print(
            f"[done] {domain}: {result['elapsed_seconds']:.1f}s  "
            f"a={result['a_min']:.3f}..{result['a_max']:.3f}  "
            f"threshold_order_ok={result['threshold_order_ok']}",
            flush=True,
        )
        gc.collect()


if __name__ == "__main__":
    main()
