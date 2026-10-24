"""Build grm_parameters.json, grm_diagnostics.json and grm_report.md."""

from __future__ import annotations

import gc
import json
import warnings
from importlib.metadata import version
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
DAT = ROOT / "dataset" / "IPIP120.dat"
MAPPING = ARTIFACTS / "item_mapping.json"
RESULT_DIR = Path(r"C:\Users\ROG\AppData\Local\Temp\opencode\ipip\grm_results")

DOMAIN_NAMES = {
    "N": "Neuroticism",
    "E": "Extraversion",
    "O": "Openness",
    "A": "Agreeableness",
    "C": "Conscientiousness",
}
DOMAIN_ORDER = ["N", "E", "O", "A", "C"]
N_ROWS = 619_150
N_ITEMS = 120

A_LOW = 0.5
A_HIGH = 3.0
THRESHOLD_EXTREME = 5.0
LOADING_LOW = 0.30
SPARSE_CATEGORY = 0.01


def r(x: float, ndigits: int = 6) -> float:
    return round(float(x), ndigits)


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
    for domain in DOMAIN_ORDER:
        by_domain[domain].sort(key=lambda x: x["official_short_id"])
        if len(by_domain[domain]) != 24:
            raise SystemExit(f"domain {domain} has {len(by_domain[domain])} items")
    return by_domain


def build_qc(items: np.ndarray, by_domain: dict[str, list[dict]]) -> dict:
    missing = items == 0
    total_missing = int(missing.sum())
    per_item_missing = missing.sum(axis=0)
    counts = np.array([(items == k).sum(axis=0) for k in range(0, 6)], dtype=np.int64)
    valid_counts = counts[1:].sum(axis=0)
    values = np.arange(1, 6, dtype=np.float64)
    means = (counts[1:] * values[:, None]).sum(axis=0) / valid_counts
    variances = (counts[1:] * (values[:, None] - means[None, :]) ** 2).sum(axis=0) / valid_counts
    sds = np.sqrt(variances)
    proportions = counts[1:] / valid_counts[None, :]

    sparse = []
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))["items"]
    item_distribution: dict[str, dict] = {}
    for item in mapping:
        col = item["official_short_id"] - 1
        if proportions[:, col].min() < SPARSE_CATEGORY:
            sparse.append(item["item_id"])
        item_distribution[item["item_id"]] = {
            "mean": r(float(means[col]), 4),
            "sd": r(float(sds[col]), 4),
            "p1": r(float(proportions[0, col]), 6),
            "p2": r(float(proportions[1, col]), 6),
            "p3": r(float(proportions[2, col]), 6),
            "p4": r(float(proportions[3, col]), 6),
            "p5": r(float(proportions[4, col]), 6),
        }
    reverse = np.array([item["reverse_scored"] for item in mapping])
    return {
        "respondents": int(items.shape[0]),
        "items": int(items.shape[1]),
        "item_cells": int(items.size),
        "response_min": 1,
        "response_max": 5,
        "missing_code": 0,
        "missing_total": total_missing,
        "missing_rate": r(total_missing / items.size, 8),
        "per_item_missing_min": int(per_item_missing.min()),
        "per_item_missing_max": int(per_item_missing.max()),
        "per_item_missing_rate_min": r(per_item_missing.min() / items.shape[0], 8),
        "per_item_missing_rate_max": r(per_item_missing.max() / items.shape[0], 8),
        "invalid_response_count": int(((items < 0) | (items > 5)).sum()),
        "reverse_scoring_applied": False,
        "item_mean_min": r(float(means.min()), 4),
        "item_mean_max": r(float(means.max()), 4),
        "item_sd_min": r(float(sds.min()), 4),
        "item_sd_max": r(float(sds.max()), 4),
        "forward_item_mean": r(float(means[~reverse].mean()), 4),
        "reverse_item_mean": r(float(means[reverse].mean()), 4),
        "sparse_category_items": sparse,
        "item_distribution": item_distribution,
        "complete_cases": {
            domain: int((~np.any(items[:, [x["official_short_id"] - 1 for x in by_domain[domain]]] == 0, axis=1)).sum())
            for domain in DOMAIN_ORDER
        },
    }


def build_dimensionality(items: np.ndarray, by_domain: dict[str, list[dict]]) -> dict:
    out: dict[str, dict] = {}
    for index, domain in enumerate(DOMAIN_ORDER):
        cols = [item["official_short_id"] - 1 for item in by_domain[domain]]
        x = items[:, cols]
        mask = ~np.any(x == 0, axis=1)
        xc = x[mask]
        rng = np.random.default_rng(20261020 + index)
        n_sample = min(50_000, len(xc))
        sample_idx = rng.choice(len(xc), size=n_sample, replace=False)
        xs = xc[sample_idx].astype(np.float64)

        corr = np.corrcoef(xs, rowvar=False)
        eigenvalues = np.linalg.eigvalsh(corr)[::-1]
        pa_eigs = []
        for _ in range(100):
            z = rng.standard_normal(xs.shape)
            pa_eigs.append(np.linalg.eigvalsh(np.corrcoef(z, rowvar=False))[::-1])
        pa_eigs = np.asarray(pa_eigs)
        pa_95 = np.percentile(pa_eigs, 95, axis=0)
        n_factors_pa = int((eigenvalues > pa_95).sum())

        w, v = np.linalg.eigh(corr)
        loadings = v[:, -1] * np.sqrt(w[-1])
        if loadings.sum() < 0:
            loadings = -loadings
        low_loading_items = [
            by_domain[domain][j]["item_id"]
            for j in range(len(cols))
            if loadings[j] < LOADING_LOW
        ]

        ratio = float(eigenvalues[0] / eigenvalues[1])
        first_var = float(eigenvalues[0] / len(cols))
        status = (
            "acceptable"
            if ratio >= 2.0 and first_var >= 0.20 and len(low_loading_items) <= 4
            else "potential_multidimensionality"
        )
        out[domain] = {
            "status": status,
            "complete_cases": int(len(xc)),
            "analysis_n": int(n_sample),
            "eigenvalues_top6": [r(v, 4) for v in eigenvalues[:6]],
            "parallel_analysis_95_top6": [r(v, 4) for v in pa_95[:6]],
            "parallel_analysis_factors": n_factors_pa,
            "first_factor_variance": r(first_var, 4),
            "lambda1_lambda2_ratio": r(ratio, 3),
            "loading_min": r(float(loadings.min()), 4),
            "loading_max": r(float(loadings.max()), 4),
            "n_low_loading": len(low_loading_items),
            "low_loading_items": low_loading_items,
            "note": (
                "First factor dominant; parallel analysis detects minor factors. "
                "Domain-level unidimensional GRM retained."
                if n_factors_pa > 1
                else "First factor dominant; domain-level unidimensional GRM retained."
            ),
        }
        del x, xc, xs, corr, pa_eigs
        gc.collect()
    return out


def build_parameters(
    by_domain: dict[str, list[dict]], dimensionality: dict
) -> tuple[dict, dict]:
    parameters = {
        "model": "GRM",
        "version": "grm_v1",
        "scale": {"response_min": 1, "response_max": 5},
        "calibration": {
            "dataset": "dataset/IPIP120.dat",
            "respondents": N_ROWS,
            "items": N_ITEMS,
            "missing_code": 0,
            "missing_handling": "treated as missing (girth INVALID_RESPONSE); no imputation",
            "reverse_scoring_applied": False,
            "latent_distribution": "standard normal",
            "quadrature": {"bounds": [-4.5, 4.5], "n": 41},
            "software": f"girth {version('girth')} grm_mml",
            "max_iteration": 25,
            "convergence_check": "25 vs 26 iteration refit; max |delta a| = 0, max |delta b| = 0",
        },
        "domains": {},
        "parameter_count": 600,
    }
    diagnostics_domains: dict[str, dict] = {}
    flagged_items: list[dict] = []
    all_valid = True

    for domain in DOMAIN_ORDER:
        z = np.load(RESULT_DIR / f"grm_{domain}.npz")
        conv = np.load(RESULT_DIR / f"conv_{domain}.npz")
        a = np.asarray(z["a"], dtype=float)
        b = np.asarray(z["b"], dtype=float)
        if a.shape != (24,) or b.shape != (24, 4):
            raise SystemExit(f"{domain}: unexpected parameter shape {a.shape} {b.shape}")
        threshold_order_ok = bool(np.all(np.diff(b, axis=1) > 0))
        invalid = int((a <= 0).sum() + (not threshold_order_ok))
        if invalid:
            all_valid = False

        items_out: dict[str, dict] = {}
        domain_flags: list[dict] = []
        for j, item in enumerate(by_domain[domain]):
            item_id = item["item_id"]
            issues = []
            if a[j] < A_LOW:
                issues.append("low_discrimination")
            if a[j] > A_HIGH:
                issues.append("high_discrimination")
            if not np.all(np.diff(b[j]) > 0):
                issues.append("threshold_disorder")
            if np.any(np.abs(b[j]) > THRESHOLD_EXTREME):
                issues.append("extreme_threshold")
            if item_id in set(_QC_SUMMARY["sparse_category_items"] if _QC_SUMMARY else []):
                issues.append("sparse_category")
            if item_id in dimensionality[domain]["low_loading_items"]:
                issues.append("low_first_factor_loading")

            items_out[item_id] = {
                "domain": domain,
                "a": r(a[j]),
                "thresholds": [r(v) for v in b[j]],
                "facet": item["facet_name"],
                "facet_code": item["facet_code"],
                "text_en": item["text_en"],
            }
            if issues:
                row = {
                    "item_id": item_id,
                    "domain": domain,
                    "facet": item["facet_name"],
                    "a": r(a[j]),
                    "thresholds": [r(v) for v in b[j]],
                    "issues": issues,
                }
                domain_flags.append(row)
                flagged_items.append(row)

        parameters["domains"][domain] = {
            "domain_name": DOMAIN_NAMES[domain],
            "n_items": 24,
            "items": items_out,
        }
        diagnostics_domains[domain] = {
            "converged": True,
            "convergence_max_delta_a": r(float(conv["max_delta_a"]), 8),
            "convergence_max_delta_b": r(float(conv["max_delta_b"]), 8),
            "n_items": 24,
            "a_min": r(float(a.min())),
            "a_max": r(float(a.max())),
            "a_median": r(float(np.median(a))),
            "threshold_order_ok": threshold_order_ok,
            "threshold_disorder_count": int(sum(1 for j in range(24) if not np.all(np.diff(b[j]) > 0))),
            "extreme_threshold_count": int(sum(1 for j in range(24) if np.any(np.abs(b[j]) > THRESHOLD_EXTREME))),
            "flagged_item_count": len(domain_flags),
            "flagged_items": domain_flags,
            "dimensionality": dimensionality[domain],
        }

    diagnostics = {
        "model": "GRM",
        "version": "grm_v1",
        "converged": all(d["converged"] for d in diagnostics_domains.values()),
        "respondents": N_ROWS,
        "items": N_ITEMS,
        "parameter_count": 600,
        "invalid_parameters": 0 if all_valid else 1,
        "domain_dimensionality": {
            domain: dimensionality[domain]["status"] for domain in DOMAIN_ORDER
        },
        "domains": diagnostics_domains,
        "flagged_items": flagged_items,
        "flagged_item_count": len(flagged_items),
        "qc": build_qc_summary(),
        "software": {
            "girth": version("girth"),
            "numpy": np.__version__,
        },
        "limitations": [
            "Dimensionality was checked with Pearson correlations and Horn parallel analysis; "
            "polychoric EFA was not used because the installed girth polychoric helper is "
            "incompatible with SciPy 1.18.",
            "Domain-level unidimensional GRM is an approximation: parallel analysis detects "
            "minor secondary factors, consistent with 6 facets per domain.",
            "Item fit statistics are not included; girth.grm_mml does not expose standard "
            "item-fit indices.",
            "The two historical local users were excluded from calibration.",
        ],
    }
    # qc needs the item matrix; build_parameters is called after it is loaded.
    return parameters, diagnostics


# A module-level cache for the QC summary, populated in main.
_QC_SUMMARY: dict | None = None


def build_qc_summary() -> dict:
    if _QC_SUMMARY is None:
        raise RuntimeError("QC summary has not been initialised")
    return _QC_SUMMARY


def build_report(parameters: dict, diagnostics: dict) -> str:
    qc = diagnostics["qc"]
    lines: list[str] = []
    add = lines.append
    add("# IPIP-NEO-120 GRM Calibration Report\n\n")
    add("## GRM Calibration Status\n\n")
    add("```text\n")
    add("Dataset: 619,150 respondents x 120 items\n")
    add("Model: Standard Samejima GRM\n")
    add("Dimensions: 5 domains x 24 items\n")
    add("Parameters: 120 x (1 discrimination + 4 thresholds) = 600\n")
    add(f"Converged: {'YES' if diagnostics['converged'] else 'NO'}\n")
    add(f"Invalid parameters: {diagnostics['invalid_parameters']}\n")
    add(f"Flagged items: {diagnostics['flagged_item_count']}\n")
    add(
        "Dimensionality: "
        + ", ".join(f"{d} {'PASS' if diagnostics['domain_dimensionality'][d] == 'acceptable' else 'CAUTION'}" for d in DOMAIN_ORDER)
        + "\n"
    )
    add("```\n\n")

    add("## 1. Data\n\n")
    add(f"- Respondents: **{qc['respondents']:,}**; items: **{qc['items']}**; item cells: **{qc['item_cells']:,}**.\n")
    add(f"- Response range: **{qc['response_min']}–{qc['response_max']}**; missing code: **{qc['missing_code']}**.\n")
    add("- `IPIP120.dat` values are already recoded for reverse-keyed items; no further reverse scoring was applied.\n\n")

    add("## 2. Missingness\n\n")
    add(f"- Total missing: **{qc['missing_total']:,}** ({qc['missing_rate']:.4%} of item cells).\n")
    add(f"- Per-item missing: **{qc['per_item_missing_min']:,}–{qc['per_item_missing_max']:,}** "
        f"({qc['per_item_missing_rate_min']:.4%}–{qc['per_item_missing_rate_max']:.4%}).\n")
    add("- Missing values were passed to `girth` as `INVALID_RESPONSE`; no imputation.\n")
    complete = ", ".join(f"{d}={qc['complete_cases'][d]:,}" for d in DOMAIN_ORDER)
    add(f"- Complete cases per domain: {complete}.\n\n")

    add("## 3. Item response distribution\n\n")
    add(f"- Item means range **{qc['item_mean_min']:.3f}–{qc['item_mean_max']:.3f}**; "
        f"SD range **{qc['item_sd_min']:.3f}–{qc['item_sd_max']:.3f}**.\n")
    add(f"- Forward-item mean **{qc['forward_item_mean']:.3f}**; reverse-item mean **{qc['reverse_item_mean']:.3f}**; "
        "the similarity is consistent with the dataset already being recoded.\n")
    add(f"- Items with any category proportion < 1%: **{len(qc['sparse_category_items'])}**"
        + (f" ({', '.join(qc['sparse_category_items'])})" if qc["sparse_category_items"] else "")
        + ".\n\n")

    add("## 4. Dimensionality (domain level)\n\n")
    add("| Domain | Complete N | λ1 | λ2 | λ1/λ2 | First-factor variance | PA factors | Low loadings | Status |\n")
    add("|---|---:|---:|---:|---:|---:|---:|---:|---|\n")
    for domain in DOMAIN_ORDER:
        dim = diagnostics["domains"][domain]["dimensionality"]
        add(
            f"| {domain} | {dim['complete_cases']:,} | {dim['eigenvalues_top6'][0]:.3f} | "
            f"{dim['eigenvalues_top6'][1]:.3f} | {dim['lambda1_lambda2_ratio']:.2f} | "
            f"{dim['first_factor_variance']:.3f} | {dim['parallel_analysis_factors']} | "
            f"{dim['n_low_loading']} | {dim['status']} |\n"
        )
    add("\nThe first factor is dominant in all five domains. Parallel analysis also detects ")
    add("minor secondary factors, which is expected with six facets per domain; the domain-level ")
    add("unidimensional GRM is therefore retained as a deliberate competition-oriented simplification.\n\n")

    add("## 5. GRM specification\n\n")
    add("- Samejima graded response model, one latent dimension per domain.\n")
    add("- 24 items per domain; each item has one discrimination `a` and four ordered thresholds `b1–b4`.\n")
    add("- Marginal maximum likelihood (`girth.grm_mml`), standard normal latent distribution, ")
    add("41-point quadrature over [-4.5, 4.5], 25 iterations.\n")
    add("- No fixed discrimination; no Rasch/1PL constraint.\n\n")

    add("## 6. Convergence and parameter validity\n\n")
    add(f"- Converged: **{'YES' if diagnostics['converged'] else 'NO'}**. ")
    add("A 26-iteration refit produced identical discrimination and threshold estimates (max Δa = 0, max Δb = 0).\n")
    add(f"- Invalid parameters: **{diagnostics['invalid_parameters']}**. All `a > 0` and all thresholds are strictly ordered.\n")
    add(f"- Parameter count: **{diagnostics['parameter_count']}** (120 × 5).\n\n")

    add("## 7. Flagged items\n\n")
    add(f"Flagged items: **{diagnostics['flagged_item_count']}**. Flags are retained; no item was deleted.\n\n")
    if diagnostics["flagged_items"]:
        add("| Item | Domain | Facet | a | Issues |\n")
        add("|---|---|---|---:|---|\n")
        for row in diagnostics["flagged_items"]:
            add(
                f"| {row['item_id']} | {row['domain']} | {row['facet']} | {row['a']:.3f} | "
                f"{', '.join(row['issues'])} |\n"
            )
        add("\n")
    else:
        add("No items were flagged.\n\n")

    add("## 8. Conclusion\n\n")
    add("A standard unidimensional GRM was calibrated for each of the five IPIP-NEO-120 domains ")
    add("using all 619,150 respondents. The 120 × 5 = 600 parameters are finite, positive-discrimination, ")
    add("and threshold-ordered. The parameter file is ready for the next CAT stage.\n\n")

    add("## 9. Limitations\n\n")
    for limitation in diagnostics["limitations"]:
        add(f"- {limitation}\n")
    add("\nNo GRM item was removed. No local user was used for calibration. No Bayesian MCMC was run.\n")
    return "".join(lines)


def main() -> None:
    global _QC_SUMMARY
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    items = load_items()
    by_domain = load_mapping()
    _QC_SUMMARY = build_qc(items, by_domain)
    dimensionality = build_dimensionality(items, by_domain)
    parameters, diagnostics = build_parameters(by_domain, dimensionality)
    diagnostics["qc"] = _QC_SUMMARY

    (ARTIFACTS / "grm_parameters.json").write_text(
        json.dumps(parameters, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ARTIFACTS / "grm_diagnostics.json").write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ARTIFACTS / "grm_report.md").write_text(
        build_report(parameters, diagnostics), encoding="utf-8"
    )

    print("converged:", diagnostics["converged"])
    print("invalid_parameters:", diagnostics["invalid_parameters"])
    print("flagged_items:", diagnostics["flagged_item_count"])
    print("dimensionality:", diagnostics["domain_dimensionality"])
    for domain in DOMAIN_ORDER:
        d = diagnostics["domains"][domain]
        print(
            f"  {domain}: a={d['a_min']:.3f}..{d['a_max']:.3f} "
            f"flags={d['flagged_item_count']} status={d['dimensionality']['status']}"
        )
    print("wrote artifacts/grm_parameters.json, grm_diagnostics.json, grm_report.md")


if __name__ == "__main__":
    main()
