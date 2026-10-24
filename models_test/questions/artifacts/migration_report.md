# IPIP-NEO-120 Data Migration Report

## Status

**PASS** — the official N4 metadata has been adopted in the production `questions.json`. The identity/order mapping is 120/120, the legacy scoring path exactly reproduces the two historical users, and the four legacy metadata corrections are documented. Canonical scores differ from the legacy scores only at those four corrected items.

| Item | Result |
|---|---|
| Official items | 120 |
| Local items | 120 |
| Identity mapping | 120/120 |
| Missing identity mappings | 0 |
| Duplicate mappings | 0 |
| Ambiguous identity mappings | 0 |
| Unverified identity mappings | 0 |
| Legacy metadata corrections | 4 (adopted) |
| Non-blocking naming normalizations | 8 |
| Production question bank | `questions.json` |
| Scoring | `scoring.py` (canonical + legacy audit) |
| Existing users migrated | 2/2 found |
| Legacy regression | PASS (exact) |
| Canonical old==new | NO for 4 corrected items; YES everywhere else |
| GRM/CAT started | NO |

## 1. Source of truth

- `dataset/DAT120.doc` — variable layout and response coding.
- `dataset/IPIP120.dat` — 619,150 respondent records.
- `dataset/IPIP-NEO-ItemKey.xls` — official Full#, Short#, Sign, Key, Facet, Item.
- `questions.json` — production canonical bank (official order, N4 metadata).
- `tests/fixtures/legacy_questions.json` — archived legacy bank for audit only.
- `tests/fixtures/legacy_results.json` — archived historical results for audit only.

The task text mentions three existing users, but only two complete result files exist. No third file was found anywhere under the repository.

## 2. Official dataset format

- Fixed-width ASCII, **151 characters per record**, **CRLF**, **153 bytes per record**.
- **619,150 rows**; file size **94,729,950 bytes**.
- No header. Respondent ID is `CASE` (positions 1–6).
- Non-item variables: `CASE, SEX, AGE, SEC, MIN, HOUR, DAY, MONTH, YEAR, COUNTRY`.
- Items `I1` … `I120` at 1-indexed positions **32 … 151**, one character each.
- Response scale **1–5**; missing value **0**.
- Missing cells: **367,593**; rows with any missing: **208,774** (33.72%).
- Reverse-scored items were already recoded in `IPIP120.dat`; raw local responses use `6 - response` when `reverse_scored` is true.

## 3. Official item key

**120 items**, **5 domains x 24**, **30 facets x 4**, **65 positive** and **55 negative** items.

| Domain | Items |
|---|---:|
| N | 24 |
| E | 24 |
| O | 24 |
| A | 24 |
| C | 24 |

- `artifacts/official_item_key_120.xlsx` is the Excel-facing view. `Sign` is stored as text so Excel displays `+N1` / `-A2` correctly.
- Machine-readable data lives in `artifacts/item_mapping.json`.

## 4. Empirical dataset ↔ item-key verification

- Mean correlation at lag 30: **0.4684**
- Mean correlation at lag 60: **0.4471**
- Mean correlation at lag 90: **0.4422**
- Mean off-diagonal correlation: **0.0398**
- Mean within-facet correlation: **0.4569** (180 pairs; listwise N = 410,376).

The 30/60/90 lag peaks are exactly what the four 30-item facet cycles predict. This proves `I{k}` is the official item with `Short# = k`.

## 5. Legacy corrections adopted

The legacy bank had 29 facets: Friendliness had 8 items and Neuroticism had 20. The four missing N4 items were corrected and adopted:

| Item | Legacy (archived) | Adopted canonical | Dataset evidence |
|---|---|---|---|
| IPIP_016 | Extraversion / Friendliness / reverse=True | Neuroticism / Self-Consciousness / reverse=False (`N4`) | Dataset correlations place this item with the other N4 items, not with E1 items (see the validation block in dataset_schema.json). |
| IPIP_046 | Extraversion / Friendliness / reverse=True | Neuroticism / Self-Consciousness / reverse=False (`N4`) | Dataset correlations place this item with the other N4 items, not with E1 items (see the validation block in dataset_schema.json). |
| IPIP_076 | Extraversion / Friendliness / reverse=True | Neuroticism / Self-Consciousness / reverse=False (`N4`) | Dataset correlations place this item with the other N4 items, not with E1 items (see the validation block in dataset_schema.json). |
| IPIP_106 | Extraversion / Friendliness / reverse=False | Neuroticism / Self-Consciousness / reverse=True (`N4`) | Dataset correlations place this item with the other N4 items, not with E1 items (see the validation block in dataset_schema.json). |

`mapping_issues.json` records the same four items with status `resolved`.

## 6. Item identity and mapping

Canonical id: `IPIP_001` … `IPIP_120`, derived from the official `Short#` column. The array index is never used as identity. Each mapping row has official Domain/Facet/Sign/Reverse, dataset column, local id/text, and legacy audit metadata. The mapping is 120 → 120, one-to-one, with no missing, duplicate or ambiguous identity.

## 7. Scoring

- `score_canonical()` uses the official metadata and is keyed by `item_id`.
- `score_legacy()` reproduces the pre-migration `eval.py` scores for audit.
- `eval.py` defaults to `questions.json` and canonical mode; `--mode legacy` is available only for historical reproduction.

```text
question bank -> official order -> item_id -> response
              -> reverse scoring (6 - response) -> facet -> domain
```

## 8. Existing users

| User | File | Items | Raw responses | Legacy exact | Legacy facets | Canonical facets |
|---|---|---:|---|---|---:|---:|
| dxl | `results/result_dxl.json` | 120 | True | True | 29 | 30 |
| zjh | `results/result_zjh.json` | 120 | True | True | 29 | 30 |

### Canonical vs legacy score changes

The only differences are the four corrected N4 items:

| User | Domain diffs | Facet diffs |
|---|---|---|
| dxl | `extraversion` 64 -> 58 (-6), average -> low<br>`neuroticism` 79 -> 97 (+18), average -> high | `friendliness` 13 -> 7 (-6), average -> low<br>`self_consciousness` absent -> 18, new level high |
| zjh | `extraversion` 67 -> 61 (-6)<br>`neuroticism` 70 -> 88 (+18), average -> high | `friendliness` 16 -> 10 (-6), high -> average<br>`self_consciousness` absent -> 18, new level high |

All other domain and facet scores are identical. Raw responses are preserved item-for-item. The archived legacy scores are stored in each result's `migration.legacy_domains` / `migration.legacy_facets` block.

## 9. Production assets

**Data / code**

- `questions.json` — canonical 120-item bank in official order.
- `results/result_dxl.json`, `results/result_zjh.json` — canonical results.
- `artifacts/item_mapping.json` — 120-item official mapping.
- `artifacts/dataset_schema.json` — official `.dat` schema + validation.
- `artifacts/official_item_key_120.xlsx` — official key, Excel-facing.
- `scoring.py`, `eval.py`, `migrate_results.py`.

**Documentation**

- `PROGRESS.md` — goal, current stage, next steps.
- `artifacts/migration_report.md` — this report.
- `artifacts/mapping_report.md` — human-readable 120-row mapping.
- `artifacts/mapping_issues.json` — the four adopted corrections.

**Audit fixtures only**

- `tests/fixtures/legacy_questions.json`
- `tests/fixtures/legacy_results.json`

## 10. Not modified

- `dataset/DAT120.doc`, `dataset/IPIP120.dat`, `dataset/IPIP-NEO-ItemKey.xls`.

## 11. Data loss and unresolved issues

- Raw responses: none lost; 120/120 preserved for both users.
- Identity mapping: no missing, duplicate or ambiguous items.
- Legacy metadata corrections: 4, all adopted and documented.
- Unresolved mapping issues: none.
- The task expects three users; only two complete result files exist.

## 12. GRM / CAT status

No GRM fitting, no item parameter estimation, no `item_parameters.json`, and no CAT work was performed. The 619k matrix was used only to verify item identity/order. The two local users were used only for migration regression.

## 13. Reproduce

```powershell
python scripts/build_official_key_assets.py   # XLS -> XLSX
python scripts/build_artifacts.py             # mapping/schema/questions.json
python scripts/verify_official_dataset.py     # full .dat validation
python migrate_results.py                     # legacy regression + canonical results
python scripts/build_migration_report.py      # this report
python -m pytest                              # 49 tests
```

Expected: **49 passed**.
