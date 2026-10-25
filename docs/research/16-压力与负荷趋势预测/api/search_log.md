# 方向16 检索日志（search log）

- **检索日期**：2026-10-17
- **检索渠道**：
  1. **OpenAlex API**（`api.openalex.org/works?search=…&per-page=4&select=id,doi,title,publication_year,primary_location,cited_by_count,authorships`）：28 组关键词检索，去重后候选约 300 条；（另 3 条 `https://doi.org/{DOI}` 取 `abstract_inverted_index` 补全摘要）
  2. **Crossref REST API**（`api.crossref.org/works/{DOI}`）：19 个候选 DOI 逐条核验题名/作者/年/卷期页/类型（其中 1 组批量为 429，改用 OpenAlex 后全部完成）
  3. **Europe PMC REST API**（`www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:…&format=json&resultType=core`）：14 条采纳文献取得摘要（PMID/PMCID）
- **采纳**：18 篇（peer-reviewed 期刊论文 / 顶会论文 / 系统综述 / 元分析 / 权威奠基文献）
- **与既有方向的去重**：方向6 [1][2][18][19][20]（双通道、慢变量、来源预测力）、方向5 [13]（负荷突变危害）、方向5 [18]（晨间恢复/日级波动）不重复收录，仅作锚点引用；另已检索但未采纳：Parkes (1990) 定速/自定速（DOI:10.1177/001872089003200207，核验通过，列入 papers.md §4.1 表格但未独立成卡，可在后续按需补卡）。
- **中文库（CNKI/万方）**：未检索（沿用方向6 结论：压力/学业关键词中文检索相关度低）。

## 检索式清单（28 组，OpenAlex search 参数原文）

### 第一轮（16 组）
1. `affective forecasting knowing what to want`
2. `A two process model of sleep regulation Borbely`
3. `Predictions from the three-process model of alertness`
4. `daily inventory of stressful events Almeida diary`
5. `Stress adaptation and disease allostasis and allostatic load McEwen`
6. `Daily stress recognition from mobile phone data weather conditions individual traits`
7. `Stress recognition using wearable sensors and mobile phones`
8. `Individuals stress assessment using human-smartphone interaction analysis`
9. `Job demands job decision latitude and mental strain Karasek`
10. `temporal factor of change in stressor-strain relationships growth curve East Germany`
11. `Recovery Experience Questionnaire development validation recuperation unwinding work`
12. `within-person fluctuations in job demands and psychological strain diary`
13. `predicting next-day mood smartphone sensing machine learning`
14. `workload transition cognitive performance adaptation cost`
15. `two-process model biomathematical fatigue performance validation`
16. `machine paced work performance`

### 第二轮（12 组）
17. `Karasek job demands decision latitude mental strain Administrative Science Quarterly 1979`
18. `Wilson Gilbert affective forecasting current directions psychological science`
19. `Klasnja micro-randomized trial experimental design just-in-time adaptive intervention`
20. `sleep duration next-day cognitive performance meta-analysis`
21. `stress prediction machine learning wearable systematic review accuracy`
22. `daily job stressors next-day affect spillover diary within-person`
23. `workload fluctuation within-person wellbeing diary`
24. `decision rules just-in-time adaptive intervention tailoring variables`
25. `EWMA control chart statistical process control monitoring`
26. `Almeida resilience vulnerability daily stressors diary`
27. `stress forecasting physiological signals prediction future state`
28. `Franken Kley work-related stressor lagged effect within-person`

### 补充：OpenAlex 按 DOI 取摘要（3 条）
- `https://api.openalex.org/works/https://doi.org/10.1111/j.0963-7214.2005.00355.x`（Wilson & Gilbert 2005）
- `https://api.openalex.org/works/https://doi.org/10.1037//0021-9010.85.3.417`（Garst et al. 2000）
- `https://api.openalex.org/works/https://doi.org/10.1080/02678373.2023.2251124`（Keller & Meier 2023）
- `https://api.openalex.org/works/https://doi.org/10.1007/s12160-016-9830-8`（Nahum-Shani et al.，取被引数）

## 采纳映射（检索式 → 采纳卡片）

| 搜索式 | 采纳卡片 |
|---|---|
| #2 #15 #16（两过程模型 / 生物数学 / 定速） | [9] [10] [11] |
| #4 / #26（日压力源日记 / 韧性） | [15] |
| #5（allostasis） | [16] |
| #6 #7 #8 #13 #21（压力识别/预测 + ML 综述） | [1] [2] [3] [4] [5] [6] [7] |
| #10 #12 #23（压力源-紧张时间动态 / 波动） | [12] [14] |
| #11（恢复体验） | [13] |
| #18（affective forecasting） | [8] |
| #24（JITAI 决策规则） | [17] [18] |
| 补充 DOI 查询 | [8][12][14] 摘要；[17] 被引数 |

## 备选未采纳（留档备查）

- `Klasnja micro-randomized trial`（#19）→ MRT 设计论文多篇（Walton 2020/2021 arXiv；Golbus 2024 Circ Cardiovasc Qual Outcomes）——与 JITAI [17][18] 重叠，未独立成卡；MRT 已在 RO-8 引用，如需可补。
- `EWMA control chart`（#25）→ 工程统计过程控制文献，无健康领域应用权重，未采纳（EWMA 已作为工程方法在 RO-2 使用，标【工程】）。
- `Parkes 1990 paced/unpaced work`（#16 命中，DOI:10.1177/001872089003200207）→ 定速控制证据，核验通过；未独立成卡（§4.1 引用其结论），可按需补卡。
- `Karasek 1979` 原始文献（#9 #17）→ Crossref 无 DOI 直取，命中为其衍生实证（Wall 1996、Kuper 2003），未采纳；demand-control 的缓冲作用已由 REQ [13] 与方向5 [18] 覆盖。
- `Haandersson? no`——`stress forecasting physiological signals prediction future state`（#27）→ 命中 PhysioFormer (2025 PLoS ONE)、HRV-AI 综述（Haque 2023 Cognitive Computation）等，均为"当前/短窗检测"，与被采纳综述 [6][7] 重叠，未独立成卡。