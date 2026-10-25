# IPIP-NEO-120 Official Item Mapping
This table maps every local question to the official IPIP-NEO-120 item identity, dataset column, domain, facet, and direction.
Official items: **120** · Local items: **120** · Identity mapping: **120/120** · Legacy metadata corrections: **4** (adopted in `questions.json`)
`item_id` is `IPIP_001` ... `IPIP_120`, derived from the official `Short#` column. `dataset_column` is the fixed-width variable `I1` ... `I120` in `IPIP120.dat` (character positions 32..151).
The local bank is already in the same order as the official `Short#` order, but array order is **not** used as identity. Every local text was checked against the official English item text.
Eight non-blocking naming normalizations (hyphen/space only) are listed separately in `mapping_issues.json`: IPIP_020, IPIP_022, IPIP_050, IPIP_052, IPIP_080, IPIP_082, IPIP_110, IPIP_112.
Excel-facing asset: `official_item_key_120.xlsx` stores the exact `Sign` text (`+N1` / `-A2`) as text. The original `.xls` remains the source of truth.
## 120-item crosswalk

| Official order | Item ID | Dataset column | Local ID | Old order | Domain | Facet | Sign | Reverse | Status |
|---:|---|---|---:|---:|---|---|---|---:|---|
| 1 | IPIP_001 | I1 | 1 | 1 | N | Anxiety | +N1 | false | ok |
| 2 | IPIP_002 | I2 | 2 | 2 | E | Friendliness | +E1 | false | ok |
| 3 | IPIP_003 | I3 | 3 | 3 | O | Imagination | +O1 | false | ok |
| 4 | IPIP_004 | I4 | 4 | 4 | A | Trust | +A1 | false | ok |
| 5 | IPIP_005 | I5 | 5 | 5 | C | Self-Efficacy | +C1 | false | ok |
| 6 | IPIP_006 | I6 | 6 | 6 | N | Anger | +N2 | false | ok |
| 7 | IPIP_007 | I7 | 7 | 7 | E | Gregariousness | +E2 | false | ok |
| 8 | IPIP_008 | I8 | 8 | 8 | O | Artistic Interests | +O2 | false | ok |
| 9 | IPIP_009 | I9 | 9 | 9 | A | Morality | -A2 | true | ok |
| 10 | IPIP_010 | I10 | 10 | 10 | C | Orderliness | +C2 | false | ok |
| 11 | IPIP_011 | I11 | 11 | 11 | N | Depression | +N3 | false | ok |
| 12 | IPIP_012 | I12 | 12 | 12 | E | Assertiveness | +E3 | false | ok |
| 13 | IPIP_013 | I13 | 13 | 13 | O | Emotionality | +O3 | false | ok |
| 14 | IPIP_014 | I14 | 14 | 14 | A | Altruism | +A3 | false | ok |
| 15 | IPIP_015 | I15 | 15 | 15 | C | Dutifulness | +C3 | false | ok |
| 16 | IPIP_016 | I16 | 16 | 16 | N | Self-Consciousness | +N4 | false | adopted: N/N4 Self-Consciousness, reverse=false |
| 17 | IPIP_017 | I17 | 17 | 17 | E | Activity Level | +E4 | false | ok |
| 18 | IPIP_018 | I18 | 18 | 18 | O | Adventurousness | +O4 | false | ok |
| 19 | IPIP_019 | I19 | 19 | 19 | A | Cooperation | -A4 | true | ok |
| 20 | IPIP_020 | I20 | 20 | 20 | C | Achievement-Striving | +C4 | false | ok |
| 21 | IPIP_021 | I21 | 21 | 21 | N | Immoderation | +N5 | false | ok |
| 22 | IPIP_022 | I22 | 22 | 22 | E | Excitement-Seeking | +E5 | false | ok |
| 23 | IPIP_023 | I23 | 23 | 23 | O | Intellect | +O5 | false | ok |
| 24 | IPIP_024 | I24 | 24 | 24 | A | Modesty | -A5 | true | ok |
| 25 | IPIP_025 | I25 | 25 | 25 | C | Self-Discipline | +C5 | false | ok |
| 26 | IPIP_026 | I26 | 26 | 26 | N | Vulnerability | +N6 | false | ok |
| 27 | IPIP_027 | I27 | 27 | 27 | E | Cheerfulness | +E6 | false | ok |
| 28 | IPIP_028 | I28 | 28 | 28 | O | Liberalism | +O6 | false | ok |
| 29 | IPIP_029 | I29 | 29 | 29 | A | Sympathy | +A6 | false | ok |
| 30 | IPIP_030 | I30 | 30 | 30 | C | Cautiousness | -C6 | true | ok |
| 31 | IPIP_031 | I31 | 31 | 31 | N | Anxiety | +N1 | false | ok |
| 32 | IPIP_032 | I32 | 32 | 32 | E | Friendliness | +E1 | false | ok |
| 33 | IPIP_033 | I33 | 33 | 33 | O | Imagination | +O1 | false | ok |
| 34 | IPIP_034 | I34 | 34 | 34 | A | Trust | +A1 | false | ok |
| 35 | IPIP_035 | I35 | 35 | 35 | C | Self-Efficacy | +C1 | false | ok |
| 36 | IPIP_036 | I36 | 36 | 36 | N | Anger | +N2 | false | ok |
| 37 | IPIP_037 | I37 | 37 | 37 | E | Gregariousness | +E2 | false | ok |
| 38 | IPIP_038 | I38 | 38 | 38 | O | Artistic Interests | +O2 | false | ok |
| 39 | IPIP_039 | I39 | 39 | 39 | A | Morality | -A2 | true | ok |
| 40 | IPIP_040 | I40 | 40 | 40 | C | Orderliness | -C2 | true | ok |
| 41 | IPIP_041 | I41 | 41 | 41 | N | Depression | +N3 | false | ok |
| 42 | IPIP_042 | I42 | 42 | 42 | E | Assertiveness | +E3 | false | ok |
| 43 | IPIP_043 | I43 | 43 | 43 | O | Emotionality | +O3 | false | ok |
| 44 | IPIP_044 | I44 | 44 | 44 | A | Altruism | +A3 | false | ok |
| 45 | IPIP_045 | I45 | 45 | 45 | C | Dutifulness | +C3 | false | ok |
| 46 | IPIP_046 | I46 | 46 | 46 | N | Self-Consciousness | +N4 | false | adopted: N/N4 Self-Consciousness, reverse=false |
| 47 | IPIP_047 | I47 | 47 | 47 | E | Activity Level | +E4 | false | ok |
| 48 | IPIP_048 | I48 | 48 | 48 | O | Adventurousness | -O4 | true | ok |
| 49 | IPIP_049 | I49 | 49 | 49 | A | Cooperation | -A4 | true | ok |
| 50 | IPIP_050 | I50 | 50 | 50 | C | Achievement-Striving | +C4 | false | ok |
| 51 | IPIP_051 | I51 | 51 | 51 | N | Immoderation | -N5 | true | ok |
| 52 | IPIP_052 | I52 | 52 | 52 | E | Excitement-Seeking | +E5 | false | ok |
| 53 | IPIP_053 | I53 | 53 | 53 | O | Intellect | -O5 | true | ok |
| 54 | IPIP_054 | I54 | 54 | 54 | A | Modesty | -A5 | true | ok |
| 55 | IPIP_055 | I55 | 55 | 55 | C | Self-Discipline | +C5 | false | ok |
| 56 | IPIP_056 | I56 | 56 | 56 | N | Vulnerability | +N6 | false | ok |
| 57 | IPIP_057 | I57 | 57 | 57 | E | Cheerfulness | +E6 | false | ok |
| 58 | IPIP_058 | I58 | 58 | 58 | O | Liberalism | +O6 | false | ok |
| 59 | IPIP_059 | I59 | 59 | 59 | A | Sympathy | +A6 | false | ok |
| 60 | IPIP_060 | I60 | 60 | 60 | C | Cautiousness | -C6 | true | ok |
| 61 | IPIP_061 | I61 | 61 | 61 | N | Anxiety | +N1 | false | ok |
| 62 | IPIP_062 | I62 | 62 | 62 | E | Friendliness | -E1 | true | ok |
| 63 | IPIP_063 | I63 | 63 | 63 | O | Imagination | +O1 | false | ok |
| 64 | IPIP_064 | I64 | 64 | 64 | A | Trust | +A1 | false | ok |
| 65 | IPIP_065 | I65 | 65 | 65 | C | Self-Efficacy | +C1 | false | ok |
| 66 | IPIP_066 | I66 | 66 | 66 | N | Anger | +N2 | false | ok |
| 67 | IPIP_067 | I67 | 67 | 67 | E | Gregariousness | -E2 | true | ok |
| 68 | IPIP_068 | I68 | 68 | 68 | O | Artistic Interests | -O2 | true | ok |
| 69 | IPIP_069 | I69 | 69 | 69 | A | Morality | -A2 | true | ok |
| 70 | IPIP_070 | I70 | 70 | 70 | C | Orderliness | -C2 | true | ok |
| 71 | IPIP_071 | I71 | 71 | 71 | N | Depression | +N3 | false | ok |
| 72 | IPIP_072 | I72 | 72 | 72 | E | Assertiveness | +E3 | false | ok |
| 73 | IPIP_073 | I73 | 73 | 73 | O | Emotionality | -O3 | true | ok |
| 74 | IPIP_074 | I74 | 74 | 74 | A | Altruism | -A3 | true | ok |
| 75 | IPIP_075 | I75 | 75 | 75 | C | Dutifulness | -C3 | true | ok |
| 76 | IPIP_076 | I76 | 76 | 76 | N | Self-Consciousness | +N4 | false | adopted: N/N4 Self-Consciousness, reverse=false |
| 77 | IPIP_077 | I77 | 77 | 77 | E | Activity Level | +E4 | false | ok |
| 78 | IPIP_078 | I78 | 78 | 78 | O | Adventurousness | -O4 | true | ok |
| 79 | IPIP_079 | I79 | 79 | 79 | A | Cooperation | -A4 | true | ok |
| 80 | IPIP_080 | I80 | 80 | 80 | C | Achievement-Striving | -C4 | true | ok |
| 81 | IPIP_081 | I81 | 81 | 81 | N | Immoderation | -N5 | true | ok |
| 82 | IPIP_082 | I82 | 82 | 82 | E | Excitement-Seeking | +E5 | false | ok |
| 83 | IPIP_083 | I83 | 83 | 83 | O | Intellect | -O5 | true | ok |
| 84 | IPIP_084 | I84 | 84 | 84 | A | Modesty | -A5 | true | ok |
| 85 | IPIP_085 | I85 | 85 | 85 | C | Self-Discipline | -C5 | true | ok |
| 86 | IPIP_086 | I86 | 86 | 86 | N | Vulnerability | +N6 | false | ok |
| 87 | IPIP_087 | I87 | 87 | 87 | E | Cheerfulness | +E6 | false | ok |
| 88 | IPIP_088 | I88 | 88 | 88 | O | Liberalism | -O6 | true | ok |
| 89 | IPIP_089 | I89 | 89 | 89 | A | Sympathy | -A6 | true | ok |
| 90 | IPIP_090 | I90 | 90 | 90 | C | Cautiousness | -C6 | true | ok |
| 91 | IPIP_091 | I91 | 91 | 91 | N | Anxiety | +N1 | false | ok |
| 92 | IPIP_092 | I92 | 92 | 92 | E | Friendliness | -E1 | true | ok |
| 93 | IPIP_093 | I93 | 93 | 93 | O | Imagination | +O1 | false | ok |
| 94 | IPIP_094 | I94 | 94 | 94 | A | Trust | -A1 | true | ok |
| 95 | IPIP_095 | I95 | 95 | 95 | C | Self-Efficacy | +C1 | false | ok |
| 96 | IPIP_096 | I96 | 96 | 96 | N | Anger | -N2 | true | ok |
| 97 | IPIP_097 | I97 | 97 | 97 | E | Gregariousness | -E2 | true | ok |
| 98 | IPIP_098 | I98 | 98 | 98 | O | Artistic Interests | -O2 | true | ok |
| 99 | IPIP_099 | I99 | 99 | 99 | A | Morality | -A2 | true | ok |
| 100 | IPIP_100 | I100 | 100 | 100 | C | Orderliness | -C2 | true | ok |
| 101 | IPIP_101 | I101 | 101 | 101 | N | Depression | -N3 | true | ok |
| 102 | IPIP_102 | I102 | 102 | 102 | E | Assertiveness | -E3 | true | ok |
| 103 | IPIP_103 | I103 | 103 | 103 | O | Emotionality | -O3 | true | ok |
| 104 | IPIP_104 | I104 | 104 | 104 | A | Altruism | -A3 | true | ok |
| 105 | IPIP_105 | I105 | 105 | 105 | C | Dutifulness | -C3 | true | ok |
| 106 | IPIP_106 | I106 | 106 | 106 | N | Self-Consciousness | -N4 | true | adopted: N/N4 Self-Consciousness, reverse=true |
| 107 | IPIP_107 | I107 | 107 | 107 | E | Activity Level | -E4 | true | ok |
| 108 | IPIP_108 | I108 | 108 | 108 | O | Adventurousness | -O4 | true | ok |
| 109 | IPIP_109 | I109 | 109 | 109 | A | Cooperation | -A4 | true | ok |
| 110 | IPIP_110 | I110 | 110 | 110 | C | Achievement-Striving | -C4 | true | ok |
| 111 | IPIP_111 | I111 | 111 | 111 | N | Immoderation | -N5 | true | ok |
| 112 | IPIP_112 | I112 | 112 | 112 | E | Excitement-Seeking | +E5 | false | ok |
| 113 | IPIP_113 | I113 | 113 | 113 | O | Intellect | -O5 | true | ok |
| 114 | IPIP_114 | I114 | 114 | 114 | A | Modesty | -A5 | true | ok |
| 115 | IPIP_115 | I115 | 115 | 115 | C | Self-Discipline | -C5 | true | ok |
| 116 | IPIP_116 | I116 | 116 | 116 | N | Vulnerability | -N6 | true | ok |
| 117 | IPIP_117 | I117 | 117 | 117 | E | Cheerfulness | +E6 | false | ok |
| 118 | IPIP_118 | I118 | 118 | 118 | O | Liberalism | -O6 | true | ok |
| 119 | IPIP_119 | I119 | 119 | 119 | A | Sympathy | -A6 | true | ok |
| 120 | IPIP_120 | I120 | 120 | 120 | C | Cautiousness | -C6 | true | ok |

## Legacy corrections (adopted)

These four items were `E1 / Friendliness` in the archived legacy bank (`tests/fixtures/legacy_questions.json`). The canonical `questions.json` now uses the official `N4 / Self-Consciousness` metadata. The legacy bank is kept only as a test fixture for historical regression.

| Item | Legacy (archived) | Adopted canonical | Dataset evidence |
|---|---|---|---|
| IPIP_016 | Extraversion / Friendliness / reverse=True | Neuroticism / Self-Consciousness / reverse=False (`N4`, sign `+N4`) | Dataset correlations place this item with the other N4 items, not with E1 items (see the validation block in dataset_schema.json). |
| IPIP_046 | Extraversion / Friendliness / reverse=True | Neuroticism / Self-Consciousness / reverse=False (`N4`, sign `+N4`) | Dataset correlations place this item with the other N4 items, not with E1 items (see the validation block in dataset_schema.json). |
| IPIP_076 | Extraversion / Friendliness / reverse=True | Neuroticism / Self-Consciousness / reverse=False (`N4`, sign `+N4`) | Dataset correlations place this item with the other N4 items, not with E1 items (see the validation block in dataset_schema.json). |
| IPIP_106 | Extraversion / Friendliness / reverse=False | Neuroticism / Self-Consciousness / reverse=True (`N4`, sign `-N4`) | Dataset correlations place this item with the other N4 items, not with E1 items (see the validation block in dataset_schema.json). |

## How to read this table
`questions.json` is the production canonical bank. The `Status` column is `ok` for unchanged items and `adopted` for the four corrected N4 items. The legacy bank is archived at `tests/fixtures/legacy_questions.json`; it is not a production input. Historical scores remain reproducible through `scoring.score_legacy()` for audit only.
