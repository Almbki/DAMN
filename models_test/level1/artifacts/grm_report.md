# IPIP-NEO-120 GRM Calibration Report

## GRM Calibration Status

```text
Dataset: 619,150 respondents x 120 items
Model: Standard Samejima GRM
Dimensions: 5 domains x 24 items
Parameters: 120 x (1 discrimination + 4 thresholds) = 600
Converged: YES
Invalid parameters: 0
Flagged items: 26
Dimensionality: N PASS, E PASS, O PASS, A PASS, C PASS
```

## 1. Data

- Respondents: **619,150**; items: **120**; item cells: **74,298,000**.
- Response range: **1–5**; missing code: **0**.
- `IPIP120.dat` values are already recoded for reverse-keyed items; no further reverse scoring was applied.

## 2. Missingness

- Total missing: **367,593** (0.4948% of item cells).
- Per-item missing: **785–4,375** (0.1268%–0.7066%).
- Missing values were passed to `girth` as `INVALID_RESPONSE`; no imputation.
- Complete cases per domain: N=558,777, E=551,341, O=554,018, A=557,931, C=554,765.

## 3. Item response distribution

- Item means range **2.062–4.268**; SD range **0.781–1.420**.
- Forward-item mean **3.427**; reverse-item mean **3.370**; the similarity is consistent with the dataset already being recoded.
- Items with any category proportion < 1%: **11** (IPIP_005, IPIP_014, IPIP_015, IPIP_022, IPIP_035, IPIP_044, IPIP_045, IPIP_065, IPIP_095, IPIP_099, IPIP_105).

## 4. Dimensionality (domain level)

| Domain | Complete N | λ1 | λ2 | λ1/λ2 | First-factor variance | PA factors | Low loadings | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| N | 558,777 | 7.648 | 2.297 | 3.33 | 0.319 | 5 | 2 | acceptable |
| E | 551,341 | 7.349 | 2.572 | 2.86 | 0.306 | 5 | 2 | acceptable |
| O | 554,018 | 4.880 | 2.186 | 2.23 | 0.203 | 6 | 3 | acceptable |
| A | 557,931 | 6.076 | 2.616 | 2.32 | 0.253 | 5 | 2 | acceptable |
| C | 554,765 | 7.885 | 2.331 | 3.38 | 0.329 | 5 | 0 | acceptable |

The first factor is dominant in all five domains. Parallel analysis also detects minor secondary factors, which is expected with six facets per domain; the domain-level unidimensional GRM is therefore retained as a deliberate competition-oriented simplification.

## 5. GRM specification

- Samejima graded response model, one latent dimension per domain.
- 24 items per domain; each item has one discrimination `a` and four ordered thresholds `b1–b4`.
- Marginal maximum likelihood (`girth.grm_mml`), standard normal latent distribution, 41-point quadrature over [-4.5, 4.5], 25 iterations.
- No fixed discrimination; no Rasch/1PL constraint.

## 6. Convergence and parameter validity

- Converged: **YES**. A 26-iteration refit produced identical discrimination and threshold estimates (max Δa = 0, max Δb = 0).
- Invalid parameters: **0**. All `a > 0` and all thresholds are strictly ordered.
- Parameter count: **600** (120 × 5).

## 7. Flagged items

Flagged items: **26**. Flags are retained; no item was deleted.

| Item | Domain | Facet | a | Issues |
|---|---|---|---:|---|
| IPIP_051 | N | Immoderation | 0.464 | low_discrimination, extreme_threshold, low_first_factor_loading |
| IPIP_081 | N | Immoderation | 0.504 | extreme_threshold, low_first_factor_loading |
| IPIP_017 | E | Activity Level | 0.604 | extreme_threshold |
| IPIP_022 | E | Excitement-Seeking | 1.162 | sparse_category |
| IPIP_082 | E | Excitement-Seeking | 0.474 | low_discrimination, extreme_threshold, low_first_factor_loading |
| IPIP_107 | E | Activity Level | 0.631 | extreme_threshold, low_first_factor_loading |
| IPIP_013 | O | Emotionality | 0.593 | extreme_threshold |
| IPIP_018 | O | Adventurousness | 0.578 | extreme_threshold |
| IPIP_043 | O | Emotionality | 0.680 | extreme_threshold |
| IPIP_058 | O | Liberalism | 0.392 | low_discrimination, low_first_factor_loading |
| IPIP_073 | O | Emotionality | 0.592 | extreme_threshold |
| IPIP_103 | O | Emotionality | 0.592 | extreme_threshold, low_first_factor_loading |
| IPIP_118 | O | Liberalism | 0.670 | extreme_threshold, low_first_factor_loading |
| IPIP_014 | A | Altruism | 1.364 | sparse_category |
| IPIP_044 | A | Altruism | 1.607 | sparse_category |
| IPIP_054 | A | Modesty | 0.445 | low_discrimination, extreme_threshold, low_first_factor_loading |
| IPIP_084 | A | Modesty | 0.386 | low_discrimination, extreme_threshold, low_first_factor_loading |
| IPIP_099 | A | Morality | 1.171 | sparse_category |
| IPIP_114 | A | Modesty | 0.724 | extreme_threshold |
| IPIP_005 | C | Self-Efficacy | 1.895 | sparse_category |
| IPIP_015 | C | Dutifulness | 1.155 | extreme_threshold, sparse_category |
| IPIP_035 | C | Self-Efficacy | 1.277 | sparse_category |
| IPIP_045 | C | Dutifulness | 1.025 | extreme_threshold, sparse_category |
| IPIP_065 | C | Self-Efficacy | 1.498 | sparse_category |
| IPIP_095 | C | Self-Efficacy | 1.488 | sparse_category |
| IPIP_105 | C | Dutifulness | 1.196 | sparse_category |

## 8. Conclusion

A standard unidimensional GRM was calibrated for each of the five IPIP-NEO-120 domains using all 619,150 respondents. The 120 × 5 = 600 parameters are finite, positive-discrimination, and threshold-ordered. The parameter file is ready for the next CAT stage.

## 9. Limitations

- Dimensionality was checked with Pearson correlations and Horn parallel analysis; polychoric EFA was not used because the installed girth polychoric helper is incompatible with SciPy 1.18.
- Domain-level unidimensional GRM is an approximation: parallel analysis detects minor secondary factors, consistent with 6 facets per domain.
- Item fit statistics are not included; girth.grm_mml does not expose standard item-fit indices.
- The two historical local users were excluded from calibration.

No GRM item was removed. No local user was used for calibration. No Bayesian MCMC was run.
