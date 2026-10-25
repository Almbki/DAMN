# IPIP-NEO-120 项目进度日志

最后更新：2026-10-20  
当前状态：**PASS（迁移 + GRM + Trait Model V1 完成）**  
当前阶段：Trait Model V1（5-domain Bayesian CAT）已冻结；Dynamic State Model 尚未开始  
下一步：第二层 User State / Task Prediction 模型

## 1. 总目标

把本地中文 IPIP-NEO-120 题库、评分程序和已有 120 题结果，严格对齐到官方 Johnson 2014 IPIP-NEO-120 的 item identity 与 `IPIP120.dat` 顺序，并证明：

- 本地第 X 题对应官方哪一列；
- 官方第 X 个变量对应哪一道题；
- 反向计分与官方 ItemKey 一致；
- 迁移后的题库和评分使用稳定 `item_id`，不再依赖数组下标；
- 历史评分可被精确复现，供迁移审计；
- 为后续 GRM 和 Bayesian CAT 提供干净的数据层。

本阶段**不做** GRM 拟合、不估计 item 参数、不生成 `item_parameters.json`、不用 2 个本地用户校准参数。

## 2. 当前完成度

| 项目 | 状态 |
|---|---|
| 官方 `DAT120.doc` 格式解析 | 完成 |
| 官方 `IPIP120.dat` 实际解析 | 完成（619,150 行） |
| 官方 `IPIP-NEO-ItemKey.xls` 解析 | 完成（301 行 = 表头 + 120 短表 + 180 全题库） |
| 官方 item identity / 顺序 | 完成（`IPIP_001`…`IPIP_120`） |
| 本地 120 题 → 官方 120 题映射 | 完成（120/120，一对一） |
| 官方 Domain / Facet 数量校验 | 通过（5×24，30×4） |
| 4 个 legacy 元数据修正 | 已修正并转正到 `questions.json` |
| 评分程序重构 | 完成（`scoring.py`，canonical + legacy audit） |
| 已有结果迁移 | 2/2 完成（`results/result_dxl.json`、`result_zjh.json`） |
| 历史评分回归 | PASS（legacy 路径逐项精确一致） |
| Canonical 评分 | 与历史仅在 4 题修正处不同，其他完全一致 |
| Excel 官方 key | `official_item_key_120.xlsx`，`Sign` 文本化，显示正常 |
| 测试 | 61 passed |
| GRM calibration | PASS（5 domains，600 params，converged） |
| Trait Model V1 CAT | PASS（619,150 simulated；target SE 0.35；ready） |
| Dynamic State Model | 未开始 |

## 3. 阶段清单

| # | 阶段 | 状态 | 说明 |
|---:|---|---|---|
| 1 | 检查项目与官方文件 | 完成 | `dataset/DAT120.doc`、`IPIP120.dat`、`IPIP-NEO-ItemKey.xls` |
| 2 | 解析 `DAT120.doc` | 完成 | `artifacts/dataset_schema.json` |
| 3 | 解析 `IPIP120.dat` | 完成 | 619,150 行，151 字符 + CRLF，I1–I120 在 32–151 |
| 4 | 解析 `IPIP-NEO-ItemKey.xls` | 完成 | 120 短表 + 180 全题库；5×24、30×4 |
| 5 | 建立官方 identity / order | 完成 | `IPIP_001`…`IPIP_120` |
| 6 | 本地题 → 官方题 | 完成 | 逐题人工对照，120/120 |
| 7 | 校验 120 题映射 | 完成 | 无 missing / duplicate / ambiguous identity |
| 8 | 校验本地元数据 | 完成 | 4 个 N4/E1 冲突已记录并修正 |
| 9 | 生成 canonical 题库 | 完成 | **`questions.json` 为正式生产题库** |
| 10 | 重构评分代码 | 完成 | `scoring.py`；`eval.py` 默认 canonical |
| 11 | 迁移已有结果 | 完成 | 2 个 canonical 结果在 `results/` |
| 12 | 回归测试 | 完成 | 61 passed；legacy 精确一致 |
| 13 | 生成报告 / artifacts | 完成 | 已收敛，见第 7 节 |
| 14 | 修复 Excel 显示 | 完成 | 删除 CSV；保留 XLSX，`Sign` 以文本保存 |
| 15 | 最终验证 | 完成 | 数据 hash、测试、Excel COM 检查 |
| 16 | GRM 数据 QC | 完成 | 619,150 × 120；缺失 367,593；值域 1–5 |
| 17 | 5-domain 单维性检查 | 完成 | Pearson + Horn PA；第一因子占优 |
| 18 | Standard GRM | 完成 | `girth.grm_mml`，5 domains × 24 items，600 params |
| 19 | 诊断 | 完成 | 收敛、a>0、thresholds ordered；26 flagged |
| 20 | CAT core | 完成 | `cat.py`；EAP、posterior SD/CI、max Fisher、round-robin |
| 21 | CAT simulation | 完成 | 619,150 respondents；5 domains |
| 22 | Trait Model V1 freeze | 完成 | `cat_config.json` + `cat_validation.json` |
| 23 | Dynamic State Model | 未开始 | 下一阶段 |

## 4. 关键数字

- `IPIP120.dat`：**619,150 行**；每行 **151 字符**；CRLF；**153 bytes/record**；文件 **94,729,950 bytes**。
- 题目列：`I1`…`I120`，1-indexed 位置 **32…151**。
- 响应值：**1–5**；缺失值：**0**。
- 缺失单元：**367,593**；至少一个缺失的 respondent：**208,774**（33.72%）。
- 官方短表：**120 items**；**5 domains × 24**；**30 facets × 4**；**65 positive / 55 negative**。
- 本地题库：120 items；旧版只有 **29 个 facet**（Friendliness 8，Neuroticism 20）。
- 已有完整结果：**2 个**（`dxl`、`zjh`）。任务文字提到 3 个，但仓库中只有 2 个。
- 元数据修正：**4 个**；仅命名差异（连字符/空格）：**8 个**。
- 测试：**61 passed**。
- GRM：**5 domains × 24 items**；**600 parameters**；**converged = YES**；**invalid = 0**；**flagged = 26**。
- 单维性：N/E/O/A/C 均 `acceptable`；第一因子占优，PA 检出次要因子，保留 domain-level GRM。

## 5. 4 个已修正并转正的项

| Item | 旧版（已归档） | 官方 / 现行 canonical | 数据集证据 |
|---|---|---|---|
| `IPIP_016` | E / Friendliness / reverse=true | N4 / Self-Consciousness / reverse=false | r(N4)=+0.433，r(E1)=−0.486 |
| `IPIP_046` | E / Friendliness / reverse=true | N4 / Self-Consciousness / reverse=false | r(N4)=+0.384，r(E1)=−0.372 |
| `IPIP_076` | E / Friendliness / reverse=true | N4 / Self-Consciousness / reverse=false | r(N4)=+0.377，r(E1)=−0.408 |
| `IPIP_106` | E / Friendliness / reverse=false | N4 / Self-Consciousness / reverse=true | r(N4)=+0.329，r(E1)=−0.325 |

这 4 项现在写入 `questions.json`，不再以“待决策错误”的形式存在。旧版题库仅作为审计 fixture 保存在 `tests/fixtures/legacy_questions.json`。

## 6. 历史评分回归结果

Legacy 路径对两个用户逐项精确复现：

| User | Items | Raw responses | Domain 精确一致 | Facet 精确一致 |
|---|---:|---|---|---|
| dxl | 120 | 是 | 是 | 是 |
| zjh | 120 | 是 | 是 | 是 |

Canonical 路径与历史的差异只来自 4 题修正：

| User | Neuroticism | Extraversion | Friendliness | Self-Consciousness |
|---|---:|---:|---:|---:|
| dxl | 79 → 97 (+18) | 64 → 58 (−6) | 13 → 7 (−6) | absent → 18 |
| zjh | 70 → 88 (+18) | 67 → 61 (−6) | 16 → 10 (−6) | absent → 18 |

其他 domain / facet 完全一致。原始 response 逐题保留。

## 7. 核心资产、说明文档、审计 fixture

### 核心资产（生产使用）

| 文件 | 用途 |
|---|---|
| `questions.json` | 正式 120 题题库；官方顺序、N4 元数据、稳定 `item_id` |
| `scoring.py` | 评分核心；canonical + legacy audit |
| `results/result_dxl.json` | dxl 的 canonical 结果 |
| `results/result_zjh.json` | zjh 的 canonical 结果 |
| `artifacts/item_mapping.json` | 120 题官方 mapping，GRM 的审计依据 |
| `artifacts/dataset_schema.json` | `IPIP120.dat` 固定宽度格式 + 619k 校验结果 |
| `artifacts/official_item_key_120.xlsx` | 官方 ItemKey 的 Excel 视图；`Sign` 文本化 |
| `artifacts/grm_parameters.json` | 生产 GRM 参数；120 items × (a + 4 thresholds) |
| `artifacts/grm_diagnostics.json` | 机器可读诊断；收敛、QC、单维性、flags |
| `cat.py` | Trait Model V1 核心：Bayesian CAT、EAP、posterior、item selection |
| `artifacts/cat_config.json` | CAT V1 固定配置；target SE 0.35 |
| `artifacts/cat_validation.json` | 619,150 respondent 的 CAT 验证指标 |

### 说明文档

| 文件 | 用途 |
|---|---|
| `PROGRESS.md` | 本日志：目标、进度、核心资产、下一步 |
| `交接文档.md` | 新文件夹/第二层模型交接说明 |
| `artifacts/migration_report.md` | 完整迁移报告 |
| `artifacts/mapping_report.md` | 人类可读的 120 行 mapping 表 |
| `artifacts/mapping_issues.json` | 4 个修正项的审计记录，status=resolved |
| `artifacts/grm_report.md` | GRM 标定简短报告 |

### 审计 fixture（不是生产数据）

| 文件 | 用途 |
|---|---|
| `tests/fixtures/legacy_questions.json` | 旧版 29-facet 题库快照；仅用于回归 |
| `tests/fixtures/legacy_results.json` | 旧版 2 个用户结果；仅用于回归 |

### 工具脚本

| 文件 | 用途 |
|---|---|
| `scripts/build_official_key_assets.py` | XLS → `official_item_key_120.xlsx` |
| `scripts/build_artifacts.py` | XLS + legacy fixture → `questions.json`、mapping、schema |
| `scripts/verify_official_dataset.py` | 619k 数据的经验校验，写入 `dataset_schema.json` |
| `scripts/build_migration_report.py` | 生成 `migration_report.md` |
| `scripts/fit_grm_domains.py` | 5 个 domain 的 `girth.grm_mml` 拟合 |
| `scripts/build_grm_artifacts.py` | GRM 参数、诊断、报告生成 |
| `scripts/validate_cat.py` | 619k respondent 的 CAT retrospect 验证 |
| `tests/test_cat.py` | CAT 核心 + 最终 artifact 测试 |

## 8. Excel 资产说明

之前 CSV 的 `sign` 列 `+N1` / `-A2` 被 Excel 当公式，显示成 `0`、`direction`、`official_order` 等。现在已经：

- **删除** `official_item_key_120.csv`。
- **保留** `artifacts/official_item_key_120.xlsx`，`Sign` 列以文本保存，Excel 正常显示 `+N1` / `-A2`。
- XLSX 的 `Sign` 单元格 `data_type` 不是公式；已用 Excel COM 实际打开验证。
- 机器可读数据看 `artifacts/item_mapping.json`；官方原始 XLS 仍是唯一 source of truth。

## 9. 复现命令

在 `models_test/questions/` 下运行：

```powershell
python scripts/build_official_key_assets.py   # XLS -> XLSX
python scripts/build_artifacts.py             # XLS + legacy fixture -> questions.json + mapping
python scripts/verify_official_dataset.py     # 619k 数据校验 -> dataset_schema.json
python migrate_results.py                     # legacy 回归 + canonical results
python scripts/build_migration_report.py      # 生成 migration_report.md
python scripts/fit_grm_domains.py --domains N E O A C   # 全量 GRM，约 15 分钟
python scripts/build_grm_artifacts.py         # 生成 3 个 GRM artifacts
python scripts/validate_cat.py --mode compare --sample 20000
python scripts/validate_cat.py --mode final --target-se 0.35
python -m pytest                              # 61 passed
```

依赖：`pip install -r requirements-dev.txt`（numpy、pytest、xlrd、openpyxl）。

## 10. 已执行的决策

原方案 A 已执行：

> 以官方 ItemKey 为准，采用 N4 元数据；接受 2 个历史用户在 N/E 和 2 个 facet 上的分数变化；legacy 仅用于审计。

因此：

- `questions.json` 现在是 canonical N4 题库。
- `questions.canonical.json` 已删除（内容已合并到 `questions.json`）。
- `mapping_issues.json` 状态为 `resolved`，不再是 `blocked`。
- `mapping_report.md` 不再显示 `Conflict YES`；主表只显示 canonical，4 个修正项在单独小节中标注 `adopted`。
- 旧版题库和旧结果只存在于 `tests/fixtures/`，不再进入生产目录。

## 11. Trait Model V1 已完成，下一步是第二层

Trait Model V1 已经冻结：

- `cat.py`：5-domain 独立 Bayesian CAT；EAP；N(0,1) prior；posterior SD；posterior quantile 95% CI；max Fisher information at EAP；round-robin。
- `min_items = 4`，`max_items = 12`，`target_se = 0.35`。
- 619,150 官方 respondents 全量 retrospect 验证。
- 相关：N 0.971 / E 0.960 / O 0.970 / A 0.965 / C 0.956；平均 MAE 0.198；平均 10.33 题/domain；50.36% 由 target SE 停止。
- O/A 经常触发 max_items，最终 SE 约 0.40/0.41；没有 extreme-theta warning。
- `artifacts/cat_config.json` + `artifacts/cat_validation.json`。

下一步是第二层（**本阶段不要做**）：

1. User State Model：使用 `theta` + `se` + response behavior。
2. Dynamic State / Task Prediction。
3. 除非发现 bug，不要改 GRM 或 CAT V1 的参数与算法。

## 12. 变更日志

- **2026-10-20**：完成官方格式解析、619k 数据校验、120-item mapping、canonical 题库、评分重构、2 个历史结果迁移、61 个测试、全部报告。
- **2026-10-20**：修复 Excel 显示问题；删除 CSV，保留文本化 `Sign` 的 XLSX。
- **2026-10-20**：执行方案 A；`questions.canonical.json` 合并进 `questions.json` 并删除；旧题库/旧结果归档为 `tests/fixtures/`；删除冗余 JSON 和备份文件。
- **2026-10-20**：完成 5-domain Standard GRM；600 params；25 vs 26 迭代收敛检查通过；生成 `grm_parameters.json`、`grm_diagnostics.json`、`grm_report.md`。
- **2026-10-20**：完成 Trait Model V1（Bayesian CAT）；619,150 respondent 验证；选择 target SE 0.35；生成 `cat_config.json`、`cat_validation.json`。
- **2026-10-20**：新增 `交接文档.md`，用于迁移到新文件夹构建第二层模型。
- **2026-10-20**：新增本进度日志 `PROGRESS.md`。

## 13. 交接提示

- 先读本文件，再读 `artifacts/migration_report.md`、`artifacts/grm_report.md`。
- 生产题库只看 `questions.json`；不要再使用 `tests/fixtures/legacy_questions.json` 做建模。
- 旧版分数只通过 `scoring.score_legacy()` 复现，不进入 GRM。
- GRM 参数只看 `artifacts/grm_parameters.json`；26 个 flagged items 没有被删除。
- Trait 模型只看 `artifacts/cat_config.json` + `artifacts/cat_validation.json`；CAT 是 5 个独立 domain。
- 官方 `dataset/` 文件不要改写；原始 hash 记录在 `artifacts/item_mapping.json` 的 `source_hashes`。
- 只有 2 个完整结果文件，不是 3 个。
