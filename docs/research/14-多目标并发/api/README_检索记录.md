# 方向14 检索记录（2026-10-17）

## 检索式与渠道

| 步骤 | 渠道 | 检索式 / 操作 | 命中 / 结果 |
|---|---|---|---|
| 1 | Crossref REST `works/{DOI}` | 逐条精确核验 20 个候选 DOI | 17 个 ok=true；3 个 404（Riediger&Freund、Soman&Cheema、Brandstätter）；Vancouver AMR 检索失败 |
| 2 | Crossref REST `works?query.bibliographic=...` | 4 组补检（见下） | 全部命中正确元数据，修正 3 个 DOI + 定位 Vancouver 2010（实际为 JAP 而非 AMR） |
| 3 | Semantic Scholar Graph API `/paper/batch` | 20 个 DOI 批量取 abstract | HTTP 429（Too Many Requests），未纳入；改用 Crossref abstract + web 检索 |
| 4 | Crossref REST `works/{DOI}` | 二次拉 20 篇元数据（含 author、abstract 字段） | 6 篇有 Crossref abstract：[1][3][5][17][18][19] |
| 5 | parallel `web_search` | 9 组 objective（每组 2–3 个 search_queries） | 复核其余 14 篇核心结论；并查"optimal number of goals" |

### 步骤 2 的 4 组 `query.bibliographic`

1. `interference and facilitation among personal goals subjective well-being persistent goal pursuit`
   → 命中 Riediger & Freund 2004, **PSPB 30(12):1511-1523, DOI 10.1177/0146167204271184**（修正：原误记为 JPSP 87(2):216-233，DOI 10.1037/0022-3514.87.2.216 实为 404）
2. `struggle of giving up personal goals affective physiological cognitive consequences goal disengagement`
   → 命中 Brandstätter, Herrmann & Schüler 2013, **PSPB 39(12):1668-1682, DOI 10.1177/0146167213500151**（修正：原误记为 Motivation & Emotion，DOI 10.1007/s11031-012-9321-3 实为 404）
3. `when goals are counterproductive effects of violation of a rational goal subsequent behavior`
   → 命中 Soman & Cheema 2004, **JCR 31(1):52-62, DOI 10.1086/383423**（修正：原 DOI 10.1086/383426 实为另一篇 "Brand Relationship Norms"）
4. `formal computational theory of multiple-goal pursuit integrating goal-choice and goal-striving`
   → 命中 Vancouver, Weinhardt & Schmidt 2010, **JAP 95(6):985-1008, DOI 10.1037/a0020628**（修正：原误记为 Academy of Management Review；实际为 Journal of Applied Psychology）

### 步骤 5 的 9 组 web_search objective

1. Empirical evidence on optimal number of simultaneous personal goals / goal overload
2. Schmidt & DeShon 2007 dynamic goal prioritization findings
3. Steel & König 2006 temporal motivation theory formula
4. Shah Friedman Kruglanski 2002 goal shielding findings
5. Heckhausen Wrosch Schulz 2010 motivational theory life-span development engagement/disengagement criteria
6. Wrosch Scheier Carver Schulz 2003 importance of goal disengagement (Self & Identity)
7. Leroy 2009 attention residue + Fishbach & Dhar 2005 + Fishbach Dhar Zhang 2006
8. Vancouver Weinhardt Schmidt 2010 MGPM + Ordóñez 2009 Goals Gone Wild
9. Kung & Scholer 2021 "Moving Beyond Two Goals"（经 Crossref works 核验 PSPR 25(2):130-158）

## 采纳统计

- 候选去重后实际核验：20 个 DOI
- Crossref works ok：20/20（修正后）
- 含 Crossref abstract：6 篇（[1][3][5][17][18][19]）
- 摘要经 PubMed/PsycInfo/ScienceDirect/JSTOR/web 复核：14 篇
- 摘要不可得（以题名+经典定位+web 佐证为准）：2 篇（[8] Kruglanski 2002 AESP 章、[20] Hartmann & Briskorn 2010 EJOR 综述；[11] Soman & Cheema 2004 题名即核心命题）
- 最终采纳：20 篇

## 与已知锚点的关系（避免重复）

- 方向3 [20] Louro 等 2007（多目标动力学：情绪×接近度→努力分配）—— 本方向补资源竞争/优先级仲裁/形式化模型层。
- 方向3 [21] Devezer 等 2014（子目标失败→总目标承诺下降）—— 本方向 [11][12][13] 补"目标违背扩散""进度释放""子目标替代/互补"机制。
- 方向9 [4] Wrosch 等 2003 **PSPB**（不可达目标的脱离/再投入与 SWB，三项相关研究，DOI 10.1177/0146167203256921）—— 本方向 [15] 收录同作者同年 **Self and Identity** 姊妹篇（DOI 10.1080/15298860309021，"放弃为何有益"的理论论证）。两 DOI 不同、期刊不同、定位互补，非重复。

## 文件清单

- `crossref_works_verify_20261017.json` — 20 篇 Crossref works/{DOI} 核验快照（title/container/year/volume/issue/pages/authors/hasAbstract）
- `crossref_searches_20261017.json` — 4 组 query.bibliographic 原始命中（DOI 修正留档）
- `web_search_excerpts_20261017.md` — 9 组 web_search 的 objective + URL + excerpts 摘录
- `README_检索记录.md` — 本文件

## 已知局限

- Semantic Scholar Graph API 限流（429）未取到摘要；APA 期刊在 Crossref 多数无 abstract 字段，靠 PubMed/PsycInfo/ScienceDirect/web 复核。
- 中文库（CNKI/万方）未检索（无公开机检 API）。
- Liu & Layland 1973、Kruglanski 2002、Hartmann & Briskorn 2010 的结论以题名+经典定位+web 佐证为准（部分摘要不可得）。
