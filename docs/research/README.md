# docs/research —— 十一方向文献调研产物说明

本文档面向项目成员，说明 `docs/research/` 下**所有产物是什么、谁产出、何时产出、怎么用、如何复核**。

- **背景**：这是"AI 自适应任务规划系统"的前期文献调研，共 **11 个方向子目录**（01 精力与疲劳、02 拖延、03 任务拆解、04 任务耗时、05 认知负荷、06 压力与目标完成、07 时间段与节律、08 记忆与学习、09 反馈调节、10 LLM 规划与 Harness、11 个体差异）。
- **产出时间**：调研于 2026-09-19 前后执行（见各方向 `api/*_search_provenance.txt` 与 `10-LLM规划与Harness/papers.md` 头部）；跨方向汇总与落地设计已按**研究对象（RO）**拆分完成，见 `RO-1`~`RO-8`。
- **产出者**：由调研执行者（AI 辅助 + 人工筛选）在调研期间生成，**不是**可自动重跑的 CI 流水线；脚本是当时的执行留痕，供复核与补检，不保证开箱即用。
- **规模**：11 份 `papers.md`，合计采纳约 **312 篇**文献。

---

## 一、目录总览树

> 以下为实际结构（`api/` 下文件数量多，按命名族归纳，不逐一展开）。

```
docs/research/
├── AGENTS.md                        ← 【新会话必读】使用规范：证据规则、方案约束、回答模板
├── 研究状态.md                      ← 【唯一真相台账】目标/核心问题/资料/已确认结论/决策记录/未决问题
├── 术语表.md                        ← 权威术语表（90+ 条，含证据ID；新增术语写入此处）
├── README.md                        ← 本文件
├── RO-1-四问研究.md                 ← 【四问研究】Rule / User State / 统计-ML / LLM 的原始调研与系统映射
├── RO-2-模型体系.md                 ← 【模型体系】M1–M8 形态 / 特征 / 门槛 / 降级
├── RO-3-用户状态评估.md             ← 【状态评估】评估 / 引导 / 问卷 / 动态出题
├── RO-4-任务分配与调度.md           ← 【调度】优先级 / 时段 / 负荷 / 缓冲 / 重排
├── RO-5-RuleEngine与决策架构.md     ← 【规则引擎】规则设计 / 裁决 / 数据流
├── RO-6-LLM-Harness.md              ← 【Harness】门控 / 路由 / 验证 / 降本
├── RO-7-证据制度与术语.md           ← 【证据制度】防幻觉 / 术语 / 复核 / FAQ
├── RO-8-路线与验证.md               ← 【路线】P0–P3 / 埋点 / MVE / 比赛亮点
├── DOI链接验证记录.txt               ← 全方向 DOI 实测 HTTP 状态汇总（TSV）
│
├── 01-精力与疲劳/
│   ├── papers.md                    ← 引用清单 + 源链接 + 逐篇模板
│   └── api/
│       ├── f1_search_provenance.txt         ← 12 组检索式与命中数溯源
│       ├── f1_candidates_270.txt            ← 候选池（270 条，TSV）
│       ├── f1_adopted_24_core.json          ← 采纳 24 篇结构化元数据
│       ├── f1_adopted_24_readable.txt       ← 同上，可读摘要
│       └── f1_europepmc_doi_verify.txt      ← Europe PMC DOI 核验快照
│
├── 02-拖延/
│   ├── fetch_02.ps1                 ← 检索脚本（OpenAlex）
│   ├── papers.md
│   └── api/
│       ├── raw_<key>.json                  ← OpenAlex 原始返回（meta + results）
│       └── <key>.txt                       ← 由 raw 解析出的可读候选（含摘要）
│
├── 03-任务拆解/
│   ├── fetch_03.ps1                 ← 检索脚本
│   ├── queries_03_supplement.json / queries_03_supplement2.json   ← 补检索式
│   ├── dois_03.json                 ← DOI 清单（核验输入）
│   ├── papers.md
│   └── api/
│       ├── raw_<key>.json / <key>.txt      ← 原始 + 可读候选
│       ├── crossref_<key>.json             ← Crossref 按式原始
│       ├── epmc_<key>.json / .txt          ← Europe PMC 按式原始 + 可读
│       ├── candidates_03.json / .txt       ← 去重候选池
│       ├── ranked_03.txt / selected_abstracts_03.txt
│       ├── abstracts.json
│       └── verify/
│           ├── <safe_doi>.json             ← 单 DOI 权威 Crossref 元数据快照
│           └── DIGEST.txt                  ← 上述快照的可读汇总
│
├── 04-任务耗时/                     ← 结构同 03（另有 cr_<key>.txt + queries_04*.json）
├── 05-认知负荷/
│   ├── fetch_05.ps1 / fetch_05b_openalex.ps1
│   ├── papers.md
│   └── api/  (cl_<key>.txt, cl2_<key>.txt, pick_05*.txt)
├── 06-压力与目标完成/               ← fetch_06.ps1 + api/raw_*.json + *.txt
├── 07-时间段与节律/
│   ├── papers.md
│   └── api/  (f7_search_provenance.txt, f7_candidates_239.txt,
│              f7_adopted_24_core.json, f7_adopted_24_readable.txt)
│
├── 08-记忆与学习/                   ← fetch_08_openalex.ps1
│   └── api/  (_*.txt/_*.json 中间产物, crossref_*.json,
│              epmc_*.json, pubmed_*.json)
├── 09-反馈调节/                     ← fetch_09_openalex.ps1（结构同 08）
├── 10-LLM规划与Harness/
│   └── papers.md                    ← 唯一无 api/ 留档的方向（见"复核"注意）
└── 11-个体差异/
    ├── fetch_11.ps1 / fetch_11b_openalex.ps1
    ├── papers.md
    └── api/  (id_<key>.txt, id2_<key>.txt, pick_11*.txt)

（仓库根级共享脚本，位于 docs/research/ 而非某个方向内）
├── fetch_multisource.py   ├── fetch_abstracts.py   ├── fetch_picks.ps1
├── verify_dois.py         ├── verify_dois.ps1      ├── check_links.py
├── parse_raw.py           ├── aggregate_candidates.py
├── rank_candidates.py     ├── dump_abstracts.py    ├── gen_citations.py
├── find_records.py        └── map_links.py
```

> **历史快照说明**：早期的 `0-开发指导.md` 与 `00-汇总映射.md` 已删除；其内容已按研究对象分发至 `RO-1`~`RO-8`（原文件章节 → RO 的映射见 §二.6）。

---

## 二、文件类型说明（是什么 / 谁产出 / 何时产出）

### 1. `NN-方向名/papers.md` —— **主交付物**
- **是什么**：该方向的最终调研成果。三段式：① GB/T 7714 引用清单；② 源链接；③ 逐篇 13 字段分析模板。详见第三节。
- **谁产出**：调研执行者；筛选原则写在每份文件头的引用块中。
- **何时产出**：该方向检索/筛选完成后一次性写定；后续仅在复核纠错时改动。

### 2. `NN-方向名/api/` —— **可复核留档（不入 git）**
- **是什么**：检索原始数据、候选清单、去重/排序中间产物、DOI 核验快照。目的是让任何人能"从 papers.md 倒推回原始检索"。
- **不入库说明**：`api/` 下原始 JSON 合计约 70 MB，已在 `.gitignore` 中排除（`docs/research/**/api/`）；需要时用同目录 `fetch_*.ps1` / 根级 `fetch_multisource.py` 重跑生成。克隆仓库后若缺少该目录，属正常现象。
- **谁产出**：检索脚本（`fetch_*.ps1` / `fetch_multisource.py`）+ 解析/核验脚本自动写入。
- **何时产出**：与检索同步；DOI 核验在候选确定后补做。
- **常见文件族**：
  | 命名 | 内容 |
  |---|---|
  | `raw_<key>.json` | OpenAlex 单次检索原始返回（`meta` 命中数 + `results` 记录） |
  | `<key>.txt` / `cr_<key>.txt` / `epmc_<key>.txt` / `cl_<key>.txt` | 由 raw 解析出的可读候选（标题/年份/被引/DOI/摘要） |
  | `crossref_<key>.json` / `epmc_<key>.json` / `pubmed_<key>.json` | 按检索式保存的跨源原始 JSON |
  | `candidates_0X.json` / `.txt` | 去重后的候选池总表 |
  | `ranked_0X.txt` / `selected_abstracts_0X.txt` / `pick_*.txt` | 按相关性排序、入选摘要、人工挑选 |
  | `abstracts.json` / `_*.txt` / `_*.json` | 摘要合并与中间产物（`_` 前缀为 08/09 的中间文件） |
  | `fX_search_provenance.txt` | **检索式 + 命中数**溯源（01/07 为 Europe PMC） |
  | `fX_candidates_N.txt` / `fX_adopted_N_readable.txt` / `fX_adopted_N_core.json` | 候选池、采纳文献摘要、结构化元数据（01/07） |
  | `verify/<safe_doi>.json` | 单 DOI 的权威 Crossref 元数据快照（文件名 = DOI 转义） |
  | `verify/DIGEST.txt` | 上述快照的可读汇总（含 `FAIL ... HTTP 429` 等失败行，如实保留） |
  | `f1_europepmc_doi_verify.txt` | Europe PMC DOI 可解析性核验快照 |

### 3. `NN-方向名/fetch_*.ps1` / `fetch_*_openalex.ps1` —— **方向专属检索脚本**
- **是什么**：该方向实际使用的检索脚本（多为 PowerShell，调用 OpenAlex / Europe PMC / Crossref）。
- **谁产出**：调研执行者。
- **何时产出**：检索当时。
- **用法**：脚本一般以 `$PSScriptRoot` 定位同目录 `api/`，直接运行即可重跑；具体入口见脚本首行注释。**注意**：重跑会覆盖同名留档，务必先备份 `api/`。

### 4. `NN-方向名/queries_*.json` / `dois_*.json` —— **检索/核验输入**
- `queries_*.json`：形如 `[{"k": "key", "q": "query string", "arxiv": true}, ...]` 的检索式清单，供 `fetch_multisource.py` 使用。
- `dois_*.json`：形如 `["10.xxxx/...", ...]` 的 DOI 清单，供 `verify_dois.py` / `check_links.py` 核验。

### 5. 仓库根级共享脚本 —— **跨方向工具**
| 脚本 | 作用 | 用法 |
|---|---|---|
| `fetch_multisource.py` | Crossref + Europe PMC + arXiv（可选 Semantic Scholar）多源抓取 | `python fetch_multisource.py <outdir> <queries.json>` |
| `fetch_abstracts.py` | 按 DOI 清单取摘要，Europe PMC 为主、Semantic Scholar 兜底 | `python fetch_abstracts.py <outdir> <dois.json>` |
| `fetch_picks.ps1` | OpenAlex 单篇接口抓元数据+摘要（方向 5、11 使用） | 直接运行 |
| `verify_dois.py` | 按 DOI 清单取权威 Crossref 元数据，写 `api/verify/<safe>.json` + `DIGEST.txt` | `python verify_dois.py <outdir> <doi...>` |
| `verify_dois.ps1` | 批量 DOI 核验（Crossref），无 DOI 者用 OpenAlex ID | 直接运行 |
| `check_links.py` | 逐个 DOI 走 `https://doi.org/`，报 HTTP 状态（HEAD + 跟随重定向） | `python check_links.py` |
| `parse_raw.py` | OpenAlex raw JSON → 可读文本（大小写敏感键 + null 安全） | 编辑入口后运行 |
| `aggregate_candidates.py` | 合并 `api/` 下可读 `.txt` 候选为去重候选表 | 按脚本入口运行 |
| `rank_candidates.py` | 用关键词对标题+摘要打分排序（标题权重×2） | 按脚本入口运行 |
| `dump_abstracts.py` | 合并摘要来源，输出逐 DOI 摘要 digest | `python dump_abstracts.py <cand> <abs> <dois> <out>` |
| `gen_citations.py` | 用已核验 Crossref 记录生成 GB/T 7714 引用草稿 | 直接运行 |
| `find_records.py` | 在记录文件中按标题关键词检索 | `python find_records.py <records.json> <pat...>` |
| `map_links.py` | 把 DOI 列表映射到 OpenAlex/来源信息 | `python map_links.py <cand> <dois>` |

### 6. `RO-1-*.md` ~ `RO-8-*.md` —— **按研究对象（RO）组织的 8 份交付件**
- **是什么**：跨方向汇总与落地设计（早期 `00-汇总映射.md` / `0-开发指导.md` 的内容）已按**研究对象**拆分为 8 份独立文档，每份自足（目标 / 核心问题 / 资料 / 方案 / 结论 / 决策 / 未决问题 / 溯源审计 / 变更日志）。引用具体结论时仍以 `papers.md` 卡片为准。
- **章节映射**：

  | RO 文档 | 内容 | 原源（历史快照） |
  |---|---|---|
  | `RO-1-四问研究.md` | 11 方向 → 系统映射总表；Q1–Q4（规则 / User State / 统计-ML / LLM）；反直觉清单；接口契约 | `00-汇总映射.md` §一–§四、§九 |
  | `RO-2-模型体系.md` | M1–M8 模型形态 / 输入特征 / 冷启动 / 升级门槛 / 降级方案 | `0-开发指导.md` §2 |
  | `RO-3-用户状态评估.md` | 状态评估 / 注册问卷 / 每日打卡 / 任务后反馈 / 防烦 / 动态出题 | `0-开发指导.md` §3 |
  | `RO-4-任务分配与调度.md` | 优先级公式 / 时段分配 / 负荷上限 / 缓冲 / 复习插入 / 重排策略 | `0-开发指导.md` §4 |
  | `RO-5-RuleEngine与决策架构.md` | 规则对象 / 15 条 P0 规则 / 裁决顺序 / 决策核心数据流与接口 | `0-开发指导.md` §7.2–7.5；`00-汇总映射.md` §九 |
  | `RO-6-LLM-Harness.md` | LLM 门控 L0–L2 / 路由 / 验证器 / 成本与预期管理 | `0-开发指导.md` §7.1、§2.8 |
  | `RO-7-证据制度与术语.md` | 三类标记 / 五档强度 / 卡片制度 / 复核方法 / 溯源审计 / FAQ F1–F20 | `AGENTS.md`、`术语表.md`、`0-开发指导.md` 附录C、`00-汇总映射.md` §八 |
  | `RO-8-路线与验证.md` | P0–P3 路线 / 埋点总表 / MVE R1–R10 / 比赛亮点 8 条 | `0-开发指导.md` §5/§6/§8/§9 |
- **重要**：各 RO §8 是**溯源审计**——区分【文献】【外推】【工程】三类内容，并逐条认领"非文献"的工程默认值（RO-7 §4.7 为总表）。引用数字前先看对应 RO §8。

### 7. `DOI链接验证记录.txt` —— **全局 DOI 实测记录**
- **格式**：每行 `<方向ID>\t<HTTP状态>\t<PMID>\t<DOI>`，如 `f1\t200\t40169294\t10.1016/j.tics.2025.02.005`。
- **含义**：对每个采纳 DOI 实测 `https://doi.org/<DOI>` 的响应状态；`200` 直连、`302` 跟随重定向后成功、`403` 为出版商反爬拦截（DOI 服务本身可解析，**不代表文献不存在**）。

### 8. `AGENTS.md` —— **新会话使用规范（必读）**
- **是什么**：证据规则（R1–R4：只能用卡片回答、判断后带卡片ID、新术语写入术语表、方案必须多方案对比）、方案生成补充约束（C1–C6：目标透明、证据门槛、禁止清单、可失败性、冲突暴露）、卡片制度、复核方法、回答模板。
- **何时用**：任何新会话首次使用本目录资料前。

### 9. `研究状态.md` —— **按研究对象组织的台账**
- **是什么**：以**研究对象（RO）**为单位组织，§0 索引列出 RO-1 四问研究（初始调研）/ RO-2 模型体系 / RO-3 状态评估 / RO-4 调度策略 / RO-5 RuleEngine 与架构 / RO-6 LLM Harness / RO-7 证据制度 / RO-8 路线与验证。每个 RO 独立记录：目标、核心问题、参考资料（卡片ID）、已确认结论、决策记录（D-x）、未决问题。
- **注意**：四个工程问题（Q1–Q4）属于 **RO-1**，是初始调研对象，不是全文件的顶层结构。
- **使用要求**：回答前先读，回答后把结果写入**对应 RO 节**（跨越现有 RO 则新建 RO），并追加变更日志（AGENTS.md 强制）。

### 10. `术语表.md` —— **权威术语表**
- **是什么**：按 A 证据制度 / B 用户状态 / C 学习记忆 / D 模型算法 / E 调度系统 五类登记术语，含通俗解释、例子、证据ID。
- **使用要求**：任何缩写首次出现都必须能在此查到，查不到就按"新增协议"追加（AGENTS.md R3）。

---

## 三、`papers.md` 的结构说明（三段式）

每份 `papers.md` 统一为三段：

### 段① 文件头引用块（`>` 引用区）
声明检索方式（数据库/API + 检索式组数）、累计命中数、抓取评估候选数、最终采纳数、DOI 验证结论、筛选原则。**这是复核的起点**：先看这里，再对 `api/` 留档。

### 段② `## 一、采纳文献清单（GB/T 7714）`
- 编号 `[1]…[n]` 为**文内唯一引用编号**，后续逐篇模板与各 RO 文档的 `方向N [n]` 均引用它。
- 格式：`作者. 题名[J/C/EB/OL]. 刊名/会议, 年, 卷(期): 页.`，arXiv 条目用 `[EB/OL]. arXiv:xxxx, 年`。
- 10 方向额外按四个子问题分组标注文献区间。

### 段③ `## 二、源链接（按上述编号）`
- 每个编号对应 `https://doi.org/...`（可含 `（出版商 已验证 200）`）与 PubMed 链接。
- 用于快速点开原文，也用于与 `DOI链接验证记录.txt`、`api/verify/` 交叉核对。

### 段④ `## 三、逐篇分析模板`（13 字段）
每篇文献一个 `### 序号. 作者 (年) — 标题` 小节，含以下 13 个字段：

| # | 字段 | 用途 |
|---|---|---|
| 1 | 研究问题 | 该文回答什么 |
| 2 | 核心理论 | 机制/框架 |
| 3 | IV | 自变量 |
| 4 | DV | 因变量 |
| 5 | 主要结论 | 可落地的结论 |
| 6 | 证据强度 | 元分析/综述/单研究/框架等 |
| 7 | 研究局限 | 外推边界 |
| 8 | 与本项目的关系 | 对系统的意义 |
| 9 | 支持的系统设计 | 具体设计动作 |
| 10 | 可采集数据 | 日志/自评/行为信号 |
| 11 | 可形成的 User State | 候选状态字段 |
| 12 | 可成为哪一部分 | Rule / Model / Harness / Scheduler 等 |
| 13 | 推荐优先级 | ★ 等级 |

#### 13 字段逐字段通俗解释（给不熟悉心理学/ML 的开发者）

> 每篇文献都按同一张"表格"来读，这样跨 11 个方向对比时不会迷路。下面用大白话再解释一遍每个字段，并说明"读它时该问什么""它在项目里对应什么"。

| # | 字段 | 通俗解释（它到底是什么） | 读的时候该问什么 | 在本项目里对应什么 |
|---|---|---|---|---|
| 1 | **研究问题** | 这篇论文到底想回答哪一句话的问题 | "它研究的事和我们要做的功能有关吗？" | 决定这条证据是否该进我们的决策依据 |
| 2 | **核心理论** | 作者用什么框架/机制来解释现象 | "它背后的道理讲得通吗？" | 决定要不要把机制写进设计说明 |
| 3 | **IV 自变量** | 实验中"被改变/被比较"的因素（原因） | "我们系统里能控制这个因素吗？" | 对应可配置参数/规则开关 |
| 4 | **DV 因变量** | 实验中"被测量的结果"（效果） | "这个结果我们能从日志里量到吗？" | 对应埋点字段/评估指标 |
| 5 | **主要结论** | 作者最后得到了什么可落地的结论 | "一句话结论是什么？" | 直接进入 `RO-1` §4 的"研究发现"列 |
| 6 | **证据强度** | 结论有多可靠（元分析/综述/单研究…） | "这条能直接写规则，还是只能先观测？" | 归一化为 `强/中强/中/理论/⚠`，决定工程动作 |
| 7 | **研究局限** | 作者自己承认的边界（样本小、领域特殊等） | "这个结论能外推到我们的场景吗？" | 决定是否需要自己做 MVE 小实验 |
| 8 | **与本项目的关系** | 作者明确写了它对我们系统的意义 | "它解决了我们哪个模块的问题？" | 连接"文献"和"代码模块"的桥 |
| 9 | **支持的系统设计** | 具体能做什么功能/规则 | "落到工程上是什么动作？" | 需求拆条/规则清单的直接来源 |
| 10 | **可采集数据** | 系统需要记录哪些日志/自评 | "现在能采到吗？采不到怎么补？" | 埋点 schema 的候选字段 |
| 11 | **可形成的 User State** | 能沉淀成哪些用户状态变量 | "这个变量跨任务稳定吗？" | `PlannerState` 的候选字段 |
| 12 | **可成为哪一部分** | 归到 Rule / Model / Harness / Scheduler 哪类 | "该由谁执行——规则、模型还是大模型？" | 决定实现归属与优先级 |
| 13 | **推荐优先级** | 作者/调研者给的星级（★越多越该先做） | "在资源有限时先做哪个？" | 排期参考（P0/P1/P2） |

> 一句话记忆：**前 4 个字段讲"论文怎么做的"，第 5–7 个字段讲"结论可不可信"，第 8–13 个字段讲"我们怎么用"。**
>
> 说明：字段 6「证据强度」是各 `papers.md` 的**原生标注**，`RO-7` §4.2 会把它归一化为 `强/中强/中/理论/⚠`，并对其中的预印本、撤稿、"仅据题录"条目降级标注。

---

## 四、如何复核检索真实性

目标是：**任何一条 `papers.md` 结论，都能沿"引用编号 → DOI → api/ 留档 → 原始检索"逆向验证**。建议按下列顺序。

### 1. 核对检索式与命中规模
- 打开对应方向的 `api/f1_search_provenance.txt`（01/07）或 `f7_search_provenance.txt`，确认文件头声明的检索式组数与命中数一致。
- 其余方向：查看 `api/candidates_0X.txt`、`ranked_0X.txt`、`raw_*.json` 的 `meta.count`，核对该方向 `papers.md` 文件头声明的"去重后候选数/命中数"。

### 2. 核对采纳文献的 DOI 可解析性
- **方式 A（全局速查）**：打开 `docs/research/DOI链接验证记录.txt`，按方向 ID 找目标 DOI，看状态码。`200/302` 视为可解析；`403` 为反爬拦截，需以 Crossref 元数据佐证。
- **方式 B（单篇权威元数据）**：在 `NN-方向名/api/verify/` 下按 `safe_doi.json` 打开快照，核对标题、期刊、年、卷期页、作者；`verify/DIGEST.txt` 是一批 DOI 的可读汇总。
- **方式 C（重跑）**：`python check_links.py`（doi.org 实测）或 `python verify_dois.py <outdir> <doi...>`（Crossref 元数据）。重跑前先备份 `api/verify/`。

### 3. 核对"摘要/题录不可得"等降级声明
- `papers.md` 文件头会声明哪些条目"摘要不可得/仅据题录"。对应查看 `api/selected_abstracts_0X.txt`、`_accepted_abstracts.txt`、`fX_adopted_N_readable.txt` 是否确实缺少该条摘要；`DIGEST.txt` 中的 `FAIL ... HTTP 429` 等行即为当时未取到的如实记录。

### 4. 交叉核对 RO 文档
- `RO-1` §4 每条映射都在"来源"列标注 `方向N [n]`。抽查时回到对应 `papers.md` 的 `[n]` 段，确认结论与字段 5/6/8/12 一致。
- `RO-7` §4.2 已列出降级清单（如方向 04 `[7][33][39]` 预印本、方向 02 `[13]` 已撤稿、部分"仅据题录"条目），复核时优先核对这几类。

### 5. 已知留档缺口（必须知道）
- **方向 10（LLM 规划与 Harness）目前没有 `api/` 目录**，仅凭 `papers.md` 文件头声明"arXiv API + Semantic Scholar 批量核实"。若要严格复核该方向，需按文件头检索式**重新抓取留档**。
- `fetch_*.ps1` / `*.py` 是当时的执行留痕，依赖外部 API 与网络环境，**不保证当前可直接重跑**；重跑会产生与当时不同的命中（API 数据在变），这属正常现象。

---

## 五、如何基于这些产物继续工作

### 0. 先读 `AGENTS.md` 与 `研究状态.md`（强制入口）
- `AGENTS.md`：证据规则（R1–R4）、方案约束（C1–C6）、卡片制度、回答模板——**新会话必须先读**。
- `研究状态.md`：当前目标、核心问题、已确认结论（C1–C22）、决策记录（D1–D11）、未决问题（T1–T7）——**回答后必须更新**。
- `术语表.md`：回答中任何缩写/专业名词首次出现都要能在这里查到。

### 1. 再读 RO 文档（按任务查表）
8 份 RO 文档是产品/工程决策的主入口。**你要做什么 → 读哪个 RO**：

| 你要做什么 | 读哪个 RO | 重点章节 |
|---|---|---|
| 搞清"哪些科学规律 → 规则 / 状态 / 模型 / LLM"的总映射 | `RO-1-四问研究.md` | §2 Q1–Q4、§4 映射总表、§4.9 反直觉清单 |
| 建/改某个预测模型（耗时/完成/复习/状态/重排/路由/难度/打扰） | `RO-2-模型体系.md` | §4.1–4.11（含门槛与降级） |
| 设计/改问卷、打卡、动态出题、防烦 | `RO-3-用户状态评估.md` | §4.2–4.8 |
| 写 Scheduler：优先级、时段、负荷、缓冲、重排 | `RO-4-任务分配与调度.md` | §4.1–4.11 |
| 写 RuleEngine：规则对象、裁决顺序、数据流接口 | `RO-5-RuleEngine与决策架构.md` | §4.2–4.8 |
| 设计 LLM 门控 / 路由 / 验证 / 成本控制 | `RO-6-LLM-Harness.md` | §4.1–4.6 |
| 查证据标记、术语、复核方法、常见问题 | `RO-7-证据制度与术语.md` | §4.1–4.7、§5 FAQ |
| 排实施顺序、埋点、验证实验、比赛亮点 | `RO-8-路线与验证.md` | §4.1–4.4 |
| 判断某个数字是"文献结论"还是"工程默认值" | 对应 RO 的 **§8 溯源审计** | §8；总表见 `RO-7` §4.7 |

### 2. 映射到项目模块
RO 文档把结论归入以下目标模块（与仓库 `AGENTS.md` 的目标架构一致；模块名为规划态）：

| 模块 | 对应调研产物 |
|---|---|
| `RuleEngine`（唯一硬约束权威） | `RO-5`（设计）；`RO-1` §2 Q1 / §4.1（研究来源）；方向 03/05/08/09/10 |
| `Scheduler` | `RO-4`；方向 02/05/07 |
| Duration Predictor | `RO-2` §4.1；方向 01/04/11 |
| User State 模型 | `RO-3`（问卷/评估）、`RO-2` §4.4（估计）；方向 01/02/05/06/07/08/09/11 |
| Review Scheduler | `RO-2` §4.3、`RO-4` §4.7；方向 08 |
| Replanning / 反馈闭环 | `RO-4` §4.10、`RO-6`；方向 09（并结合项目既有 per-user 冷却设计） |
| LLM Router / Verifier（Harness） | `RO-6`；方向 10 |

### 3. 深入单个方向
- 需要论证某条设计决策时，打开该方向的 `papers.md`，从对应 `[n]` 段的 13 字段（尤其"研究局限""证据强度"）取原文依据。
- 需要补检/扩检时：复用同方向 `queries_*.json` 与 `fetch_*.ps1`，或使用根级 `fetch_multisource.py`；新增结果写入 `api/`，并按第三节三段式更新 `papers.md`。
- 新增 DOI 后：跑 `verify_dois.py` 生成 `api/verify/` 快照，并同步更新 `DOI链接验证记录.txt`。

### 4. 维护约定（避免破坏可复核性）
- **不要删除 `api/` 留档**；重跑检索前先备份。
- 新增文献沿用现有编号规则：`papers.md` 内 `[n]` 连续编号，各 RO 文档用 `方向N [n]` 引用。
- 新增/修订结论时，同步标注证据强度；预印本、撤稿、仅题录条目必须显式降级标注。
- `RO-1`~`RO-8` 已完成；改动其结论时请同步回看 `papers.md` 原始依据，并更新 `研究状态.md`。
