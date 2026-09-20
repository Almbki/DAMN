# 方向5：认知负荷（Cognitive Load）

**检索 N 篇，采纳 M 篇**：本方向实际执行检索 14 组关键词查询（PubMed E-utilities 13 组 + OpenAlex API 13 组，部分查询存在跨组重叠），原始命中条目 504 条，按 DOI/PMID/标题去重后 478 篇；经人工筛选采纳 **25 篇**（全部为 peer-reviewed 期刊论文/权威综述/元分析/经典著作章节）。

- 检索渠道：PubMed E-utilities（NCBI，`esearch`+`efetch`，含题录与摘要）、OpenAlex API（含被引量）、Crossref API（DOI 校验）、Semantic Scholar API（摘要补全）。原始数据保存在本目录 `api/` 子目录（13 个 PubMed 查询文件 + 13 个 OpenAlex 补充查询文件 + 3 个精选文献详情文件）。
- 筛选原则：优先 peer-reviewed / systematic review / meta-analysis / 高被引经典；优先变量可被系统观测（行为数据、自评量表、完成时间、日志）的研究；依赖 EEG/fNIRS/瞳孔等设备的研究保留理论价值并明确标记。
- 本项目背景对应：RuleEngine（硬规则）、Scheduler（排程）、Duration Predictor（时长预测）、User State（stress_response/duration_factor/completion_rate）、LLM Harness。

---

## 一、采纳文献清单（GB/T 7714 引用格式）

### A. 认知负荷理论框架（任务复杂度→负荷的机理）

[1] SWELLER J. Element interactivity and intrinsic, extraneous, and germane cognitive load[J]. Educational Psychology Review, 2010, 22(2): 123-138. DOI:10.1007/s10648-010-9128-5.

[2] SWELLER J, VAN MERRIËNBOER J J G, PAAS F. Cognitive architecture and instructional design: 20 years later[J]. Educational Psychology Review, 2019, 31(2): 261-292. DOI:10.1007/s10648-019-09465-5.

[3] KALYUGA S. Expertise reversal effect and its implications for learner-tailored instruction[J]. Educational Psychology Review, 2007, 19(4): 509-539. DOI:10.1007/s10648-007-9054-3.

[4] TETZLAFF L, SIMONSMEIER B A, PETERS T, et al. A cornerstone of adaptivity – a meta-analysis of the expertise reversal effect[J]. Learning and Instruction, 2025, 98: 102142. DOI:10.1016/j.learninstruc.2025.102142.

[5] WICKENS C D. Multiple resources and mental workload[J]. Human Factors, 2008, 50(3): 449-455. DOI:10.1518/001872008x288394.

[6] SHENHAV A, MUSSLICK S, LIEDER F, et al. Toward a rational and mechanistic account of mental effort[J]. Annual Review of Neuroscience, 2017, 40: 99-124. DOI:10.1146/annurev-neuro-072116-031526.

### B. 负荷测量与认知努力成本

[7] HART S G, STAVELAND L E. Development of NASA-TLX (Task Load Index): results of empirical and theoretical research[M]//HANCOCK P A, MESHKATI N. Advances in Psychology. North-Holland: Elsevier, 1988: 139-183. DOI:10.1016/s0166-4115(08)62386-9.

[8] YOUNG M S, BROOKHUIS K, WICKENS C D, et al. State of science: mental workload in ergonomics[J]. Ergonomics, 2014, 58(1): 1-17. DOI:10.1080/00140139.2014.956151.

[9] KOOL W, MCGUIRE J T, ROSEN Z B, et al. Decision making and the avoidance of cognitive demand[J]. Journal of Experimental Psychology: General, 2010, 139(4): 665-682. DOI:10.1037/a0020198.

[10] WESTBROOK A, BRAVER T S. Cognitive effort: a neuroeconomic approach[J]. Cognitive, Affective, & Behavioral Neuroscience, 2015, 15(2): 395-415. DOI:10.3758/s13415-015-0334-y.

### C. 疲劳、连续任务与时间累积效应

[11] WARM J S, PARASURAMAN R, MATTHEWS G. Vigilance requires hard mental work and is stressful[J]. Human Factors, 2008, 50(3): 433-441. DOI:10.1518/001872008x312152.

[12] VAN CUTSEM J, MARCORA S, DE PAUW K, et al. The effects of mental fatigue on physical performance: a systematic review[J]. Sports Medicine, 2017, 47(8): 1569-1588. DOI:10.1007/s40279-016-0672-0.

[13] COX-FUENZALIDA L-E. Effect of workload history on task performance[J]. Human Factors, 2007, 49(2): 277-291. DOI:10.1518/001872007x312496.

[14] MEIJMAN T F. Mental fatigue and the efficiency of information processing in relation to work times[J]. International Journal of Industrial Ergonomics, 1997, 20(1): 31-38. DOI:10.1016/s0169-8141(96)00029-7.

[15] HELTON W S, RUSSELL P N. Working memory load and the vigilance decrement[J]. Experimental Brain Research, 2011, 212(3): 429-437. DOI:10.1007/s00221-011-2749-1.

### D. 恢复、休息与每日状态

[16] TUCKER P. The impact of rest breaks upon accident risk, fatigue and performance: a review[J]. Work & Stress, 2003, 17(2): 123-137. DOI:10.1080/0267837031000155949.

[17] ARIGA A, LLERAS A. Brief and rare mental "breaks" keep you focused: deactivation and reactivation of task goals preempt vigilance decrements[J]. Cognition, 2011, 118(3): 439-443. DOI:10.1016/j.cognition.2010.12.007.

[18] BINNEWIES C, SONNENTAG S, MOJZA E J. Daily performance at work: feeling recovered in the morning as a predictor of day-level job performance[J]. Journal of Organizational Behavior, 2008, 30(1): 67-93. DOI:10.1002/job.541.

[19] SCHUMANN F, STEINBORN M B, KÜRTEN J, et al. Restoration of attention by rest in a multitasking world: theory, methodology, and empirical evidence[J]. Frontiers in Psychology, 2022, 13: 867978. DOI:10.3389/fpsyg.2022.867978.

### E. 学习任务的时间结构（间隔/交错）

[20] CEPEDA N J, PASHLER H, VUL E, et al. Distributed practice in verbal recall tasks: a review and quantitative synthesis[J]. Psychological Bulletin, 2006, 132(3): 354-380. DOI:10.1037/0033-2909.132.3.354.

[21] ROHRER D, DEDRICK R F, STERSHIC S. Interleaved practice improves mathematics learning[J]. Journal of Educational Psychology, 2014, 107(3): 900-908. DOI:10.1037/edu0000001.

[22] ROHRER D, DEDRICK R F, HARTWIG M K, et al. A randomized controlled trial of interleaved mathematics practice[J]. Journal of Educational Psychology, 2019, 112(1): 40-52. DOI:10.1037/edu0000367.

[23] DUNLOSKY J, RAWSON K A, MARSH E J, et al. Improving students' learning with effective learning techniques: promising directions from cognitive and educational psychology[J]. Psychological Science in the Public Interest, 2013, 14(1): 4-58. DOI:10.1177/1529100612453266.

### F. 行为数据估算与实时自适应系统

[24] FANG Y, YANG P, FRANK E, et al. Patterns of smartphone typing performance by time awake: implications for unobtrusive ambulatory mental fatigue assessment[J]. PLOS Digital Health, 2026, 5(3): e0001281. DOI:10.1371/journal.pdig.0001281.

[25] KULKARNI A R, KUBER P M. Detecting and improving human cognitive state in real-time using data-driven adaptive systems: a systematic review[J]. Bioengineering, 2026, 13(7): 734. DOI:10.3390/bioengineering13070734.

---

## 二、逐条源链接（按上文编号顺序）

[1] https://doi.org/10.1007/s10648-010-9128-5 （OpenAlex: https://openalex.org/W2040127838）
[2] https://doi.org/10.1007/s10648-019-09465-5 （OpenAlex: https://openalex.org/W2913144876）
[3] https://doi.org/10.1007/s10648-007-9054-3 （OpenAlex: https://openalex.org/W2055556052）
[4] https://doi.org/10.1016/j.learninstruc.2025.102142 （OpenAlex: https://openalex.org/W4409534651）
[5] https://doi.org/10.1518/001872008x288394 （OpenAlex: https://openalex.org/W2152905082）
[6] https://doi.org/10.1146/annurev-neuro-072116-031526 （OpenAlex: https://openalex.org/W2600886565）
[7] https://doi.org/10.1016/s0166-4115(08)62386-9 （OpenAlex: https://openalex.org/W2157289187）
[8] https://doi.org/10.1080/00140139.2014.956151 （OpenAlex: https://openalex.org/W2076883103）
[9] https://doi.org/10.1037/a0020198 （OpenAlex: https://openalex.org/W2092813663）
[10] https://doi.org/10.3758/s13415-015-0334-y （OpenAlex: https://openalex.org/W2016649766）
[11] https://doi.org/10.1518/001872008x312152 （OpenAlex: https://openalex.org/W2056699334）
[12] https://doi.org/10.1007/s40279-016-0672-0 （OpenAlex: https://openalex.org/W2563742216）
[13] https://doi.org/10.1518/001872007x312496 （OpenAlex: https://openalex.org/W2015219569）
[14] https://doi.org/10.1016/s0169-8141(96)00029-7 （OpenAlex: https://openalex.org/W2158421215）
[15] https://doi.org/10.1007/s00221-011-2749-1 （OpenAlex: https://openalex.org/W2078597588）
[16] https://doi.org/10.1080/0267837031000155949 （OpenAlex: https://openalex.org/W2010695153）
[17] https://doi.org/10.1016/j.cognition.2010.12.007 （PubMed: https://pubmed.ncbi.nlm.nih.gov/21211793/）
[18] https://doi.org/10.1002/job.541 （OpenAlex: https://openalex.org/W2025956004）
[19] https://doi.org/10.3389/fpsyg.2022.867978 （OpenAlex: https://openalex.org/W4220818821）
[20] https://doi.org/10.1037/0033-2909.132.3.354 （OpenAlex: https://openalex.org/W2049428464）
[21] https://doi.org/10.1037/edu0000001 （OpenAlex: https://openalex.org/W2116640775）
[22] https://doi.org/10.1037/edu0000367 （OpenAlex: https://openalex.org/W2945831516）
[23] https://doi.org/10.1177/1529100612453266 （OpenAlex: https://openalex.org/W2126180793）
[24] https://doi.org/10.1371/journal.pdig.0001281 （OpenAlex: https://openalex.org/W7140677945）
[25] https://doi.org/10.3390/bioengineering13070734 （OpenAlex: https://openalex.org/W7167621180）

---

## 三、逐篇分析

### [1] Element Interactivity and Intrinsic, Extraneous, and Germane Cognitive Load（Sweller, 2010）

- **研究问题**：如何用一个统一机制（元素交互性 element interactivity）同时定义内在、外在、相关三类认知负荷？
- **核心理论**：认知负荷理论（CLT）。提出元素交互性是内在负荷的基础机制，并进一步认为外在负荷与相关负荷也可用元素交互性定义（是否与任务本身本质相关来区分内在/外在）。
- **Independent Variables**：任务/教学材料的元素交互性水平（概念分析）。
- **Dependent Variables**：三类认知负荷的构成与关系（理论推导，无实验因变量）。
- **主要结论**：任务复杂度（元素交互性）是内在负荷的决定因素；教学设计若引入非本质的元素交互性则产生外在负荷；相关负荷以内在负荷为基础。所有负荷效应的解释均可统一到元素交互性。
- **结论的证据强度**：高（理论奠基性文章，被引约 2000 次；其后续实验支撑见 [2]）。
- **研究局限**：纯理论文章；元素交互性在真实任务中的操作性测量依赖专家判断。
- **与本项目的关系**：为"任务复杂度→认知负荷"提供了可操作的理论定义：**任务的内在负荷 ≈ 其元素交互性**，可由任务属性（步骤数、知识关联度、新概念数）估计。
- **可以支持什么系统设计**：给任务标注"元素交互性/内在负荷等级"；规划器据此排序任务、避免连续高负荷任务。
- **可以采集什么数据**：任务结构特征（步骤数、依赖关系、涉及新概念数）、领域专家对任务复杂度的评分。
- **可以形成什么 User State**：`task_intrinsic_load`（任务侧属性）与 `user_estimated_load`（结合个体先验知识后的预估负荷）。
- **可以作为哪一部分**：Rule/Statistical Model —— 负荷预估器（Duration Predictor 与 completion_rate 预测的特征）；LLM Harness —— 让 LLM 对任务做元素交互性标注。
- **推荐优先级**：⭐⭐⭐⭐⭐（理论基石，直接支撑"任务复杂度如何影响认知负荷"）

### [2] Cognitive Architecture and Instructional Design: 20 Years Later（Sweller, van Merriënboer & Paas, 2019）

- **研究问题**：总结认知负荷理论 20 年（1998-2018）的理论与实证进展，给出未来方向。
- **核心理论**：CLT 完整架构：工作记忆容量与时长有限，长时记忆容量无限；一切新信息先经有限工作记忆加工，存入长时记忆后"容量限制消失"。
- **Independent Variables**：教学设计的各类操纵（示例、分段、冗余、专家反转等，综述性文章）。
- **Dependent Variables**：学习与迁移绩效、主观心理努力（综述）。
- **主要结论**：知识库（长时记忆中的图式）决定工作记忆的实际处理能力；**同一任务的负荷随学习者熟练度变化**——这是个体化负荷的核心理由；教学设计应随学习者知识水平动态调整。
- **结论的证据强度**：高（两大奠基人 + Paas 的权威综述，被引约 2200）。
- **研究局限**：主要面向教学情境，未直接给出"每日任务上限"之类的量化规则。
- **与本项目的关系**：直接支持"**同一任务的负荷是因人而异的**"——Duration Predictor 必须个体化；解释为什么新手与专家的完成时间/概率差异巨大。
- **可以支持什么系统设计**：个体化任务难度分级；依据用户 skill 状态动态调整任务复杂度。
- **可以采集什么数据**：用户在该任务类型的既往完成记录、错误率、求助行为。
- **可以形成什么 User State**：`user_skill`、`duration_factor`。
- **可以作为哪一部分**：Rule（专家反转规则的依据）；Statistical Model（负荷= f(任务元素交互性, 用户先验知识)）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [3] Expertise Reversal Effect and Its Implications for Learner-Tailored Instruction（Kalyuga, 2007）

- **研究问题**：学习者先验知识水平如何调节教学技术的有效性（专家反转效应），及其对个性化教学系统的启示。
- **核心理论**：CLT + 能力倾向-处理交互（ATI）。对低先验知识者有效的指导（如示例、图示），对高先验知识者可能无效甚至有害（因冗余/重复加工）。
- **Independent Variables**：学习者先验知识水平 × 教学技术（示例、问题解决等）。
- **Dependent Variables**：学习绩效、认知负荷。
- **主要结论**：教学技术的有效性依赖学习者知识水平，最优指导随知识增长从"强指导"转向"弱指导/无指导"；这一模式支持构建学习者定制化（learner-tailored）的自适应教学系统。
- **结论的证据强度**：高（大量实验综述 + ATI 研究佐证，被引约 1000）。
- **研究局限**：主要针对学习任务，对工作任务的推广需谨慎；知识水平的实时测量是工程难点。
- **与本项目的关系**：直接支撑"**同一任务不同人完成时间/概率差异巨大**"（先验知识维度）；提示 planner 对高 skill 用户减少冗余提示。
- **可以支持什么系统设计**：任务分派时考虑用户 skill 与任务"指导需求"匹配；高 skill 用户可给更高复杂度任务。
- **可以采集什么数据**：用户在领域内的历史完成记录（对/错、时长）、诊断性测试。
- **可以形成什么 User State**：`user_skill`（领域维度）、先验知识估计。
- **可以作为哪一部分**：Rule（专家反转：高 skill + 低复杂度任务的预计时长因子下调）；Statistical Model（skill × 任务复杂度 交互项）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [4] A cornerstone of adaptivity – A meta-analysis of the expertise reversal effect（Tetzlaff 等, 2025）

- **研究问题**：用元分析检验专家反转效应在多大程度上是稳健的、可支撑自适应学习系统设计。
- **核心理论**：专家反转效应（CLT 框架内）。
- **Independent Variables**：学习者知识水平 × 指导水平/教学设计（元分析中的研究特征）。
- **Dependent Variables**：学习结果（成绩/迁移）与认知负荷（效应量）。
- **主要结论**：专家反转效应是自适应教学（adaptivity）的核心依据——指导强度必须随学习者状态自适应调节，否则对部分学习者产生负面效果（该结论为该文主题句与标题所述；原始摘要未开放，具体效应量建议获取原文核实）。
- **结论的证据强度**：中高（2025 年最新元分析，Learning and Instruction 发表；注：该文无开放摘要，具体纳入研究数与效应量待查原文）。
- **研究局限**：摘要不可得；元分析通常存在发表偏倚风险与研究异质性。
- **与本项目的关系**：为"自适应调整任务难度/指导"提供元分析层面的正当性，即系统不应给所有人相同的任务配置。
- **可以支持什么系统设计**：RuleEngine 中"根据 user_skill 调整任务难度上限/提示级别"的规则来源。
- **可以采集什么数据**：用户技能指标、任务完成质量。
- **可以形成什么 User State**：`user_skill`。
- **可以作为哪一部分**：Rule（自适应指导强度规则）；LLM Harness（为 LLM 提供"按用户水平调整解释详细程度"的 prompt 依据）。
- **推荐优先级**：⭐⭐⭐⭐（元分析证据新，但摘要不可得，建议获取全文）

### [5] Multiple Resources and Mental Workload（Wickens, 2008）

- **研究问题**：多重资源理论如何解释多任务干扰并预测工作负荷过载？
- **核心理论**：多重资源模型（4 维：加工阶段、编码模态、处理代码、视觉通道）。任务共享资源维度越多，干扰越大。
- **Independent Variables**：任务对资源维度的占用情况（理论/建模输入）。
- **Dependent Variables**：双任务绩效损耗、过载预测（与实测数据的相关性）。
- **主要结论**：资源重叠决定双任务干扰；模型对多任务绩效的预测与数据高度相关；与"工作负荷"概念部分相关，最适用于双任务过载导致的绩效崩溃。
- **结论的证据强度**：高（50 年研究总结，被引约 2100；含计算模型与模拟驾驶数据验证）。
- **研究局限**：资源维度的操作化在真实任务中不直观；对单一高复杂度任务的预测力有限。
- **与本项目的关系**：解释"连续安排多个同模态/同类任务"为何叠加疲劳与干扰；支持"数学和算法任务尽量不同天/不同时段"的直觉（同类认知过程易竞争资源）。
- **可以支持什么系统设计**：任务分派时对任务做资源维度标注，避免连续安排占用相同资源维度的任务；Scheduler 的约束输入。
- **可以采集什么数据**：任务类型标签（语言/视觉/推理/记忆负荷）、用户切换任务时的行为数据。
- **可以形成什么 User State**：`load_accumulation`（按资源维度累计）。
- **可以作为哪一部分**：Rule（连续任务资源维度冲突检测）；Statistical Model（干扰预测）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [6] Toward a Rational and Mechanistic Account of Mental Effort（Shenhav 等, 2017）

- **研究问题**：心理努力（mental effort）的机制是什么？为什么控制成本令人厌恶？如何分配努力？
- **核心理论**：努力的成本-收益（机会成本）框架：控制分配由"当前任务回报 vs 备选活动回报"决定；努力受限制且被体验为成本。
- **Independent Variables**：任务的认知控制需求、激励/回报结构（综述视角）。
- **Dependent Variables**：努力分配、任务选择、绩效（综述）。
- **主要结论**：个体会回避高认知需求（努力厌恶）；控制的分配依据期望价值计算；神经机制上与前扣带回/前额叶相关。为"为什么高认知任务会降低完成概率/坚持率"提供机制解释。
- **结论的证据强度**：高（Annual Review 权威综述，被引约 1200）。
- **研究局限**：机制层面研究多来自实验室决策任务；对"每日上限"无直接量化。
- **与本项目的关系**：直接支撑"**高认知负荷任务的完成概率低于低负荷任务**"，且用户会在任务选择/坚持中系统性地回避高努力任务。
- **可以支持什么系统设计**：对高负荷任务预留更高放弃风险；规划时避免一天内堆叠多个高努力任务；将"努力厌恶"纳入完成概率预测。
- **可以采集什么数据**：任务放弃/推迟事件、任务选择历史、自评努力。
- **可以形成什么 User State**：`effort_aversion`、`completion_rate`（高负荷任务上的历史）。
- **可以作为哪一部分**：Statistical Model（完成概率 = f(任务负荷, 用户努力厌恶)）；LLM Harness（解释规划决策给用户）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [7] Development of NASA-TLX (Task Load Index)（Hart & Staveland, 1988）

- **研究问题**：开发并验证一个多维度的主观工作负荷测量工具（NASA-TLX）。
- **核心理论**：工作负荷多维概念：心理需求、体力需求、时间需求、绩效、努力、挫折感六维；加权评分。
- **Independent Variables**：任务类型/难度（工具开发与验证中的任务条件）。
- **Dependent Variables**：六维自评得分及加权总负荷（0-100 量表）。
- **主要结论**：NASA-TLX 成为人因学领域最广泛使用的主观工作负荷量表（被引约 1.5 万次）；其六维结构可区分任务间负荷差异。（原文摘要未开放，此结论为领域公认且为工具本身之定义。）
- **结论的证据强度**：高（工具开发经典，被引量级印证其影响力）。
- **研究局限**：主观自评；依赖用户对"负荷"概念的理解；单次测量成本较高（问卷 6 项+权重比较）。
- **与本项目的关系**：为系统提供**标准化的自评负荷采集工具**；用户可在任务完成后 30 秒内给出六维评分，作为 User State 更新与 Duration Predictor 校准的依据。
- **可以支持什么系统设计**：任务后自评打卡（可选）；将 NASA-TLX 六维得分降维成单值 load score。
- **可以采集什么数据**：任务后 TLX 六维评分、耗时。
- **可以形成什么 User State**：`stress_response`、`perceived_load`（任务的用户感知负荷）。
- **可以作为哪一部分**：Statistical Model（感知负荷的回归/校准标签）；LLM Harness（将自评解释为自然语言反馈）。
- **推荐优先级**：⭐⭐⭐⭐⭐（测量工具直接落地）

### [8] State of science: mental workload in ergonomics（Young 等, 2014）

- **研究问题**：综述人因学领域 30 年来心理工作负荷（MWL）的理解、测量与应用现状。
- **核心理论**：MWL 的多种定义；负荷-绩效关系存在"上限"——负荷超过耐受点时绩效崩溃。
- **Independent Variables**：任务需求水平、系统设计（综述）。
- **Dependent Variables**：绩效、主观负荷、生理指标（综述）。
- **主要结论**：MWL 概念模糊但重要；强调**量化工作负荷"红线"（workload redlines）**——定义操作者接近或超过绩效耐受点的时刻，是应用研究的核心挑战之一。
- **结论的证据强度**：高（Ergonomics 权威综述，被引约 940）。
- **研究局限**：指出 MWL 定义/测量缺乏统一标准；"红线"目前难以普遍量化。
- **与本项目的关系**：直接对应"**个体化负荷上限**"问题——文献承认存在个体绩效耐受点，但没有普适的单一数值，须个体化估计。
- **可以支持什么系统设计**：为每个用户估计其负荷红线（基于历史负荷-绩效关系）；负荷逼近红线时降低任务难度或插入缓冲。
- **可以采集什么数据**：负荷自评 + 完成质量/时长的联合序列（负荷-绩效曲线）。
- **可以形成什么 User State**：`workload_redline`（个体化负荷上限）、`duration_factor`。
- **可以作为哪一部分**：Rule（接近红线触发调整的阈值规则）；Statistical Model（负荷-绩效曲线的断点估计）。
- **推荐优先级**：⭐⭐⭐⭐⭐（"每日上限"的直接学术依据：上限存在但须个体化）

### [9] Decision making and the avoidance of cognitive demand（Kool 等, 2010）

- **研究问题**：人是否真的回避认知需求（"省力法则"是否适用于认知努力）？
- **核心理论**：最小努力原则（law of less work）扩展到认知领域。
- **Independent Variables**：可自由选择的任务路径（高/低认知需求操作），6 个实验操纵需求水平。
- **Dependent Variables**：路径选择偏好（回避认知需求的比例）。
- **主要结论**：被试系统性地偏好低认知需求路径；该偏好不受错误率、总时长、目标达成率解释，且在无意识层面发生；偏好随任务激励变化，并与执行控制个体差异相关。
- **结论的证据强度**：高（6 个行为实验，被引约 1200，领域里程碑）。
- **研究局限**：实验室任务选择范式；真实工作场景中的回避更隐蔽。
- **与本项目的关系**：机制层面解释"高认知任务的**完成概率更低、更容易被推迟/放弃**"；支持对任务做负荷排序和"一天内高认知任务数量限制"的经验规则。
- **可以支持什么系统设计**：任务推荐顺序中穿插低负荷任务；对高负荷任务设置更宽容的排期（如上午清醒时段）。
- **可以采集什么数据**：用户任务选择顺序、推迟/跳过行为日志。
- **可以形成什么 User State**：`effort_aversion`、任务级 `completion_rate`。
- **可以作为哪一部分**：Statistical Model（选择/完成概率模型）；LLM Harness（向用户解释"为什么今天不安排连续高难任务"）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [10] Cognitive effort: A neuroeconomic approach（Westbrook & Braver, 2015）

- **研究问题**：如何对认知努力给出操作性定义与度量？神经经济学框架的优势？
- **核心理论**：努力-价值决策：将认知努力视为成本，在成本-收益权衡中做决策；提出用"努力折扣/价格"量化个体的努力成本。
- **Independent Variables**：任务认知需求、奖励数量（框架性综述）。
- **Dependent Variables**：选择行为、努力折扣率、生理/自评努力指标（综述）。
- **主要结论**：神经经济框架比自评与自主神经标记更有推论力；可估计个体的"努力成本曲线"，从而预测其在何种需求/奖励组合下会放弃任务。
- **结论的证据强度**：中高（综述 + 行为/神经证据，被引约 630）。
- **研究局限**：主要停留于实验室范式；努力折扣率的实测任务较重。
- **与本项目的关系**：提供"**个体化负荷上限**"的可测量概念——努力成本曲线（多久后用户会放弃）。
- **可以支持什么系统设计**：为每个用户估计努力折扣参数；据此动态调整任务负荷与奖励/反馈结构。
- **可以采集什么数据**：多轮"选择高回报高负荷 vs 低回报低负荷"的偏好数据（可选冷启动）；放弃/坚持行为。
- **可以形成什么 User State**：`effort_discount`（个体化努力成本参数）。
- **可以作为哪一部分**：Statistical Model（离散选择模型估计努力折扣）；Rule（高成本用户的任务负荷上限更低）。
- **推荐优先级**：⭐⭐⭐⭐

### [11] Vigilance requires hard mental work and is stressful（Warm, Parasuraman & Matthews, 2008）

- **研究问题**：警戒（vigilance）任务是否真的"不费力"？负荷与应激如何随任务时间变化？
- **核心理论**：警戒任务消耗注意资源（资源理论）；警戒衰减源于高资源需求而非"无聊/唤醒下降"。
- **Independent Variables**：任务类型（连续/同时）、任务难度、时间（任务时长内的多个时段）。
- **Dependent Variables**：命中率、反应时、主观负荷（NASA-TLX）、经颅多普勒血流速度、任务诱发应激。
- **主要结论**：警戒任务的主观负荷**高**且随加工需求增加而升高；随时间出现绩效下降（警戒衰减）；任务诱发应激上升。挑战"警戒是低负荷任务"的传统观点。
- **结论的证据强度**：高（行为+神经+主观三类证据汇聚，被引约 1250）。
- **研究局限**：警戒范式任务单调；高负荷效应在复杂任务中的外推需谨慎。
- **与本项目的关系**：支持"**长时间/连续任务导致绩效随时间下降**"（时间累积效应），且连续同类任务（如连续做题）会加速负荷累积。
- **可以支持什么系统设计**：长任务内部插入简短检查点/休息；连续任务之间安排缓冲；时长预测器对长任务增加时间衰减因子。
- **可以采集什么数据**：任务内随时间变化的命中/错误/反应时轨迹。
- **可以形成什么 User State**：`vigilance_decrement`、随时间衰减的 `duration_factor`。
- **可以作为哪一部分**：Statistical Model（时间-绩效衰减曲线）；Rule（连续同类任务上限）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [12] The Effects of Mental Fatigue on Physical Performance: A Systematic Review（Van Cutsem 等, 2017）

- **研究问题**：精神疲劳是否损害体力/耐力表现？其背后机制？
- **核心理论**：精神疲劳 = 长时间高认知活动导致的心理生物学状态；通过感知用力（RPE）上移影响耐力表现（中枢疲劳/心理生物模型）。
- **Independent Variables**：精神疲劳诱导（30 分钟以上高认知任务）vs 对照（11 项研究）。
- **Dependent Variables**：耐力表现（力竭时间、功率输出、完成时间）、RPE、生理指标。
- **主要结论**：精神疲劳显著降低耐力表现（力竭时间缩短、完成时间增加），伴随感知用力升高；生理指标多无显著变化 → 疲劳是"感知/动机"层面的。
- **结论的证据强度**：高（PRISMA 系统综述，PubMed PMID: 28044281，被引约 900）。
- **研究局限**：纳入研究多为实验室；效应大小因任务而异；排除 <30 分钟的自控耗竭任务。
- **与本项目的关系**：提供"**认知疲劳→后续任务完成时间变长/完成概率下降**"的高等级证据；支撑"高认知任务之后不要紧接另一高认知任务"。
- **可以支持什么系统设计**：高认知任务后安排低认知或休息缓冲；Duration Predictor 对疲劳状态上调时长预测。
- **可以采集什么数据**：任务历史（高认知任务时长与先后顺序）、主观疲劳评分。
- **可以形成什么 User State**：`mental_fatigue`、`stress_response`。
- **可以作为哪一部分**：Rule（高认知任务缓冲规则）；Statistical Model（疲劳状态下的时长/概率修正）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [13] Effect of Workload History on Task Performance（Cox-Fuenzalida, 2007）

- **研究问题**：任务开始前的负荷历史（负荷突然升高或降低）如何影响后续绩效？
- **核心理论**：负荷转换（workload transition）/适应模型：负荷历史的突然改变造成适应成本。
- **Independent Variables**：高→低 vs 低→高负荷条件（随机分组，198 名被试，Bakan 警戒任务）。
- **Dependent Variables**：正确反应数、反应时、总错误数。
- **主要结论**：负荷降低后绩效下降（支持既往研究）；更重要的是，**负荷突然升高或降低都会导致准确率下降和反应时变慢**，且持续较长时间；后续实验表明该衰减源于负荷转换本身而非疲劳。
- **结论的证据强度**：中高（实验研究，Human Factors，被引 84；样本量 198 人）。
- **研究局限**：警戒任务情境；实验室任务。
- **与本项目的关系**：**直接支撑"任务间缓冲"与"避免负荷突变"**：不仅高负荷任务不能连续，负荷剧烈波动本身也有代价——日程应平滑过渡。
- **可以支持什么系统设计**：任务难度渐进式变化（避免陡升陡降）；任务间安排过渡性低负荷任务或休息。
- **可以采集什么数据**：相邻任务的负荷等级差、任务切换时刻的绩效（完成时间、错误率）。
- **可以形成什么 User State**：`load_transition_cost`、`stress_response`。
- **可以作为哪一部分**：Rule（相邻任务负荷差上限）；Statistical Model（负荷变化幅度→绩效损失的预测）。
- **推荐优先级**：⭐⭐⭐⭐⭐（"任务间缓冲"的直接实验证据）

### [14] Mental fatigue and the efficiency of information processing in relation to work times（Meijman, 1997）

- **研究问题**：工作时间长度如何影响信息加工效率与精神疲劳？
- **核心理论**：长时间任务→疲劳→信息加工效率下降（时长-效率关系）。
- **Independent Variables**：工作时间/任务时长（现场或半现场研究）。
- **Dependent Variables**：信息加工效率（速度/准确率）、疲劳主观报告。
- **主要结论**：随工作时间累积，信息加工效率下降、疲劳上升；效率下降与工作时间存在系统性关系（原文摘要未开放，具体效应量待原文核实；该文为工业人因领域被引约 115 次的经典实证）。
- **结论的证据强度**：中（单一实证研究，被引约 115；无开放摘要）。
- **研究局限**：摘要不可得；20 世纪 90 年代工作任务情境。
- **与本项目的关系**：支持"**单日任务时长累积→效率下降**"，为"每日任务量上限"提供早期实证背景。
- **可以支持什么系统设计**：累计工作时长监测；超过阈值降低任务强度。
- **可以采集什么数据**：任务时长序列、每任务完成时间/错误率。
- **可以形成什么 User State**：`work_hours_accumulated`、`duration_factor`（随时间衰减）。
- **可以作为哪一部分**：Rule（每日工作量上限的初步参考）；Statistical Model（时长-效率曲线）。
- **推荐优先级**：⭐⭐⭐（摘要不可得，建议获取原文核实后再作为硬规则依据）

### [15] Working memory load and the vigilance decrement（Helton & Russell, 2011）

- **研究问题**：工作记忆负荷是否加剧警戒衰减？
- **核心理论**：警戒衰减源于高认知资源需求（工作记忆负荷消耗执行资源）。
- **Independent Variables**：同时进行的空间/言语工作记忆负荷 vs 无负荷对照（745 名被试）。
- **Dependent Variables**：目标检测反应时、感知敏感度 A′。
- **主要结论**：并发工作记忆负荷加剧警戒衰减（反应时增加、A′下降）；空间与言语负荷均产生效应，提示共用执行资源 → 支持"警戒是艰苦工作"而非"无聊"。
- **结论的证据强度**：高（大样本 745 人实验，PMID: 21643711，被引约 156）。
- **研究局限**：警戒任务范式；并发负荷范式。
- **与本项目的关系**：支持"**任务间工作记忆残留/连续高记忆负荷任务会互相加剧衰减**"。
- **可以支持什么系统设计**：避免连续安排高工作记忆负荷任务（如连续数学/编程）；任务间插入低记忆负荷活动。
- **可以采集什么数据**：任务工作记忆负荷标签（按任务类型）、切换后首个任务的绩效。
- **可以形成什么 User State**：`cognitive_state`（记忆负荷维度）。
- **可以作为哪一部分**：Rule（工作记忆负荷类任务连续上限）；Statistical Model。
- **推荐优先级**：⭐⭐⭐⭐

### [16] The impact of rest breaks upon accident risk, fatigue and performance: A review（Tucker, 2003）

- **研究问题**：休息对事故风险、疲劳与绩效的系统影响如何？休息时机与时长有最优吗？
- **核心理论**：疲劳累积与恢复；休息是维持绩效、控制风险累积的手段。
- **Independent Variables**：休息频率/时机/时长（对既有研究的综述）。
- **Dependent Variables**：事故率、绩效、疲劳（综述）。
- **主要结论**：规律休息能有效维持绩效、管理疲劳、控制长时间任务中风险累积；每 2 小时的常规休息基础上，额外的微型休息（micro-breaks）在部分条件下有益；**个体常不能主动在需要时充分休息**；休息的最优时长缺乏硬证据。
- **结论的证据强度**：中高（Work & Stress 综述，被引约 245）。
- **研究局限**：指出该领域"硬证据"稀少，尤其缺流行病学证据。
- **与本项目的关系**：直接支撑"**任务间缓冲**"规则：休息有用、时机比时长更关键、用户不会自发休息 → 系统应主动安排。
- **可以支持什么系统设计**：Scheduler 主动在任务间插入缓冲/休息；长任务中安排 micro-breaks。
- **可以采集什么数据**：休息时间戳、休息后首任务绩效、自评疲劳。
- **可以形成什么 User State**：`rest_need`、`recovery_level`。
- **可以作为哪一部分**：Rule（缓冲时段生成规则）；Statistical Model（休息后绩效恢复模型）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [17] Brief and rare mental "breaks" keep you focused（Ariga & Lleras, 2011）

- **研究问题**：短暂、罕见的"心理休息"能否阻止警戒衰减？
- **核心理论**：目标习惯化（goal habituation）而非资源耗竭导致警戒衰减；短暂停用任务目标可重置注意。
- **Independent Variables**：在警戒任务中偶尔回忆记忆中的数字（微休息）vs 只在结束时回忆。
- **Dependent Variables**：警戒命中率随时间的变化（衰减与否）。
- **主要结论**：仅需偶尔短暂转移任务目标，警戒衰减即可被避免；挑战资源耗竭解释，给出低成本、可操作的反衰减机制。
- **结论的证据强度**：高（Cognition 实验，PMID: 21211793，被引约 190）。
- **研究局限**：警戒范式；"微休息"的时长/频率参数未系统扫描。
- **与本项目的关系**：为"**任务间缓冲**"提供高性价比机制：**极短（秒级）的注意转移即可显著恢复绩效**，无需长休息。
- **可以支持什么系统设计**：任务间 1-2 分钟切换性缓冲（换脑活动）；长任务内部微休息点。
- **可以采集什么数据**：缓冲时长、缓冲前后绩效对比。
- **可以形成什么 User State**：`recovery_level`。
- **可以作为哪一部分**：Rule（最小缓冲时长下限：短缓冲也有效）；Statistical Model（缓冲-恢复曲线）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [18] Daily performance at work: feeling recovered in the morning as a predictor of day-level job performance（Binnewies, Sonnentag & Mojza, 2008）

- **研究问题**：早晨的恢复状态（身体+心理清爽）能否预测当天的工作绩效？
- **核心理论**：恢复（recovery）与绩效；日常波动（within-person）。
- **Independent Variables**：早晨恢复状态（每日测量）、工作控制（调节变量）。
- **Dependent Variables**：每日任务绩效、个人主动性、组织公民行为、补偿性努力。
- **主要结论**：早晨恢复感正向预测当日任务绩效、主动性与组织公民行为，负向预测补偿性努力；高工作控制者此关系更强（99 名员工、一周每日双测）。
- **结论的证据强度**：中高（日记法，Journal of Organizational Behavior，被引约 356）。
- **研究局限**：自评绩效为主；关联不等于因果。
- **与本项目的关系**：直接支撑"**每日任务量上限应结合当日初始状态**"：同一天内任务绩效取决于晨间恢复状态 → 系统应允许按日调整负荷预算。
- **可以支持什么系统设计**：每日开始时采集恢复自评（1 题），据此调整当日任务负荷预算（上限）。
- **可以采集什么数据**：晨间恢复感自评、当日完成率/完成时间。
- **可以形成什么 User State**：`daily_recovery`、`time_preference`。
- **可以作为哪一部分**：Rule（每日负荷上限 × 恢复系数）；Statistical Model（恢复→绩效的日级预测）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [19] Restoration of Attention by Rest in a Multitasking World（Schumann 等, 2022）

- **研究问题**：休息对注意恢复的理论与实证现状如何？如何科学研究休息？
- **核心理论**：对比资源模型（资源耗竭与恢复）与满足感模型（satiation）；提出休息的分类法（长/短/微休息）与测量框架。
- **Independent Variables**：休息的类型/时长/情境（框架性综述与理论评估）。
- **Dependent Variables**：注意绩效、疲劳、恢复指标（综述）。
- **主要结论**：休息研究缺乏统一理论与测量；给出了实验研究休息的方法论准则；强调用心理测量学与心理计时学框架重新审视休息效应。
- **结论的证据强度**：中高（方法学综述，Frontiers in Psychology，被引约 84）。
- **研究局限**：方法学导向，未给出具体休息参数建议。
- **与本项目的关系**：为"任务间缓冲"提供**理论分类与测量框架**：区分长/短/微休息，指导系统缓冲参数的设计与评估。
- **可以支持什么系统设计**：缓冲策略 A/B 测试的方法学依据；将缓冲作为可配置参数。
- **可以采集什么数据**：不同缓冲类型/时长下的任务绩效、疲劳自评。
- **可以形成什么 User State**：`recovery_level`。
- **可以作为哪一部分**：Statistical Model（缓冲效果评估设计）；LLM Harness（向用户解释恢复科学）。
- **推荐优先级**：⭐⭐⭐⭐

### [20] Distributed practice in verbal recall tasks: A review and quantitative synthesis（Cepeda 等, 2006）

- **研究问题**：间隔效应（spacing/lag）如何影响记忆保持？间隔与保持间隔的关系？
- **核心理论**：分布式练习效应。
- **Independent Variables**：练习间隔（连续 vs 分散；短 vs 长间隔）、保持间隔。
- **Dependent Variables**：最终测验保持率（839 个评估、317 个实验、184 篇文章的元分析）。
- **主要结论**：分散练习优于连续练习；**产生最大保持的练习间隔随保持间隔增长而增长**（间隔与保持间隔联合决定最佳保持）；跨 184 篇文章一致。
- **结论的证据强度**：很高（Psychological Bulletin 元分析，被引约 1900）。
- **研究局限**：主要为言语记忆任务；学习任务情境。
- **与本项目的关系**：为"**同类知识任务应隔天/隔周排布**"提供元分析级证据：相同/相近学习任务之间需要间隔，间隔长度与期望保持时长正相关。
- **可以支持什么系统设计**：复习/练习类任务的间隔调度（基于保持目标动态计算最优间隔）；不同天分配同主题任务。
- **可以采集什么数据**：任务主题标签、复习间隔、测验/自测表现。
- **可以形成什么 User State**：`retention_curve`（每主题）、`time_preference`。
- **可以作为哪一部分**：Statistical Model（间隔-保持曲线参数）；Rule（同主题任务最小间隔）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [21] Interleaved practice improves mathematics learning（Rohrer, Dedrick & Stershic, 2014）

- **研究问题**：交错练习（interleaved practice）是否优于阻塞练习（blocked practice）？
- **核心理论**：交错练习迫使学习者按问题本身选择策略（区分与检索），而非按"本节课的题型"机械套用。
- **Independent Variables**：练习安排（交错 vs 阻塞），126 名七年级学生、3 个月练习。
- **Dependent Variables**：1 天后与 30 天后的未预告测验成绩。
- **主要结论**：交错练习在即时与延迟测验上均显著更优（Cohen's d = 0.42 与 0.79）。
- **结论的证据强度**：高（教育情境 RCT，Journal of Educational Psychology，被引约 166）。
- **研究局限**：数学学科；间隔/交错联合效应未拆分。
- **与本项目的关系**：直接支撑"**数学和算法任务尽量不同天/交错安排**"：同类练习任务集中安排（阻塞）短期看似高效，长期保持差；交错安排利于迁移与保持。
- **可以支持什么系统设计**：同一技能的多项练习任务交错安排到不同天；避免"今天连续 5 道同类题"。
- **可以采集什么数据**：任务技能标签、任务完成顺序、后续同类任务表现。
- **可以形成什么 User State**：`user_skill`（按技能维度）、`retention_curve`。
- **可以作为哪一部分**：Rule（同技能任务交错规则，即"数学和算法尽量不同天"的直接依据）；Statistical Model。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [22] A randomized controlled trial of interleaved mathematics practice（Rohrer 等, 2019）

- **研究问题**：在自然课堂情境下，交错练习的大规模 RCT 效果与可行性？
- **核心理论**：交错练习效应。
- **Independent Variables**：交错 vs 阻塞作业安排（54 个七年级班级、4 个月、群随机）。
- **Dependent Variables**：1 个月后未预告测验成绩。
- **主要结论**：交错组显著优于阻塞组（61% vs 38%，d = 0.83）；教师无需培训即可实施且事后表示支持。
- **结论的证据强度**：很高（预注册群随机对照试验，Journal of Educational Psychology，被引约 93）。
- **研究局限**：仅数学；"交错作业占比"的剂量效应未系统研究。
- **与本项目的关系**：为"交错/不同天安排"提供生态效度最高的证据——真实场景、大规模、预注册。
- **可以支持什么系统设计**：Scheduler 的作业/任务交错约束的默认规则。
- **可以采集什么数据**：任务技能标签、安排模式、测验表现。
- **可以形成什么 User State**：`user_skill`。
- **可以作为哪一部分**：Rule（交错安排规则，证据强度最高）；Statistical Model。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [23] Improving Students' Learning With Effective Learning Techniques（Dunlosky 等, 2013）

- **研究问题**：10 种常见学习技术的相对效用如何？哪些值得推荐？
- **核心理论**：对学习技术按证据强度分级（高/中/低效用）；涉及练习测试、分散练习、交错练习、精加工提问等。
- **Independent Variables**：学习技术（10 种）。
- **Dependent Variables**：学习/记忆/问题解决/理解等多项标准（大规模综述）。
- **主要结论**：练习测试、分散练习、交错练习被评为高效技术；划重点、重读等为低效；效用随学习条件、学生特征（年龄/能力/先验知识）、材料与测验类型变化。
- **结论的证据强度**：很高（心理学与教育心理学权威长文综述，被引约 3100）。
- **研究局限**：主要面向学生学习情境。
- **与本项目的关系**：为任务安排提供"证据分级"方法论与具体规则来源：练习类任务的间隔与交错是最高等级证据。
- **可以支持什么系统设计**：任务类型→推荐调度策略映射表（间隔/交错/集中）。
- **可以采集什么数据**：任务类型元数据。
- **可以形成什么 User State**：`user_skill`。
- **可以作为哪一部分**：Rule（调度规则的知识库）；LLM Harness（向用户解释任务安排理由）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [24] Patterns of smartphone typing performance by time awake（Fang 等, 2026）

- **研究问题**：能否用智能手机自然打字行为无创地监测精神疲劳？
- **核心理论**：行为数字表型（digital phenotyping）；打字速度随时间清醒的变化近似实验室精神运动警觉任务（PVT）的规律。
- **Independent Variables**：清醒时长（穿戴设备推算）、打字会话（366 名住院医师、2 个月、45,042 次打字会话）。
- **Dependent Variables**：打字速度/绩效（SensorKit 指标）。
- **主要结论**：打字速度与清醒时长呈显著非线性关系：约清醒 7.5 小时达峰，15.3 小时显著下降——与实验室 PVT 在清醒 15.8 小时后反应延迟增多的经典结果高度一致。
- **结论的证据强度**：高（大样本生态数据，PLOS Digital Health；与经典 PVT 行为规律互证）。
- **研究局限**：观察性研究；打字行为受任务内容影响；个体间异质性未完全建模。
- **与本项目的关系**：为系统提供**免打扰的负荷/疲劳估算通道**：用户在电脑/手机上的输入行为（打字速度、错误率）可映射到疲劳状态，无需自评。
- **可以支持什么系统设计**：后台采集输入行为指标→疲劳估计→调整当日负荷上限；无需打断用户。
- **可以采集什么数据**：打字速度/停顿/错误率、时段、清醒时长（如可获取）。
- **可以形成什么 User State**：`mental_fatigue`（连续值）、`duration_factor`（随时间衰减）。
- **可以作为哪一部分**：Statistical Model（行为→疲劳回归模型，可直接复用其非线性关系假设）；ML。
- **推荐优先级**：⭐⭐⭐⭐⭐（行为数据可直接落地，对应本项目的 task logs）

### [25] Detecting and Improving Human Cognitive State in Real-Time Using Data-Driven Adaptive Systems: A Systematic Review（Kulkarni & Kuber, 2026）

- **研究问题**：实时认知状态感知+自适应干预系统的现状与局限？
- **核心理论**：数据驱动的认知状态感知（EEG 为主）与干预（反馈/难度调整/自动化调整）。
- **Independent Variables**：传感模态、认知状态目标（注意力 56%、心理负荷 26%）、干预类型（神经反馈 30%、难度调整 19%、自动化调整 11%）（27 项研究综述）。
- **Dependent Variables**：状态分类准确率（实验室多分类 81.85%-95.81%）、系统延迟、干预效果。
- **主要结论**：实验室分类精度很高但系统多为反应式（检测到状态后才干预，非预测式）；仅 33% 报告延迟；建议多认知状态联合检测与预测性轨迹。
- **结论的证据强度**：中高（2026 年系统综述，27 项研究）。
- **研究局限**：大部分依赖 EEG（非日常环境）；实验室-现实鸿沟。
- **与本项目的关系**：直接对应本项目的闭环"State Estimation→Adjustment"：确认**从行为/生理信号估计认知状态并自适应调整任务是成熟范式**；同时指出本项目应做**预测式**（在状态恶化前调整）而非反应式。
- **可以支持什么系统设计**：状态估计→规则触发的难度调整/缓冲插入；将"预测性状态轨迹"作为设计目标。
- **可以采集什么数据**：任务内行为指标（速度、错误、中断）、自评状态。
- **可以形成什么 User State**：`cognitive_state`（注意力/负荷/警觉多维度）。
- **可以作为哪一部分**：ML（状态分类）；Rule（状态阈值→调整动作）；LLM Harness（调整动作的自然语言解释）。
- **推荐优先级**：⭐⭐⭐⭐⭐

---

## 四、针对项目"经验规则"的文献支持度判定（特别分析）

1. **"高认知任务不能连续"** —— 支持度：**强**。[12]（系统综述：精神疲劳损害后续表现）、[5]（资源重叠导致干扰）、[11]（警戒衰减）、[15]（工作记忆负荷加剧衰减）、[13]（负荷历史效应：突变本身有害）。理论链条完整：高认知任务消耗资源/诱导疲劳→后续任务完成时间变长、完成概率下降。但"完全不能连续"是强表述，文献支持的是"连续高负荷任务会累积损伤绩效"，因此更准确的规则是"连续高负荷任务之间存在缓冲/降级"。

2. **"数学和算法尽量不同天"** —— 支持度：**强（有 RCT 与元分析）**。[21][22]（交错练习 RCT：d=0.42-0.83）、[20]（间隔效应元分析：最佳间隔随保持目标增长）、[23]（交错与分散练习被评为最高证据等级技术）。注意：这些证据针对**学习/练习类任务**，对"纯执行类任务"（如写代码交付）证据较弱；若任务目的只是产出而非练习，规则适用性需调低。

3. **"每日任务量上限"** —— 支持度：**中（概念成立，数值须个体化）**。[8] 明确承认"workload redlines"概念但承认难以普适量化；[18] 支持按日调整（晨间恢复感×绩效）；[14] 早期实证支持时长累积效应。结论：**存在个体化上限，但文献不支持任何普适固定数值**——上限必须由系统根据个体历史估计。

4. **"任务间缓冲"** —— 支持度：**强**。[16]（综述：规律休息维持绩效，时机比时长关键）、[17]（秒级微休息即可阻止衰减）、[19]（缓冲研究框架）、[13]（负荷突变代价→缓冲平滑过渡）。最短缓冲可低至秒-分钟级；缓冲内容宜为低负荷切换（非发呆）。

5. **"个体化负荷上限"** —— 支持度：**中强（方向明确，参数需估计）**。[8][10]（努力成本曲线个体差异）、[18]（日间状态波动）、[24]（行为指标个体化监测）、[3][4]（专家反转：同一任务负荷因人而异）。系统应基于每人的"负荷-绩效历史"估计其红线，而不是用固定阈值。
