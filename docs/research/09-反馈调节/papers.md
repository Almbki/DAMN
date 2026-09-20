# 方向9：反馈调节 / 自适应规划（Feedback Regulation & Adaptive Planning）文献调研

> **检索 388 篇（去重后可核验记录），采纳 31 篇。**
>
> - 检索时间：2026-09-19
> - 检索 API：Europe PMC REST（覆盖 MEDLINE/PubMed）、NCBI PubMed E-utilities、Crossref REST
> - 原始检索数据：本目录 `./api/`（含 `epmc_*.json`、`pubmed_*.json`、`crossref_*.json`、`_verified_titles_*.json`、`_citation_meta.json`、`_abstracts_dump.txt`）
> - 筛选原则：优先 peer-reviewed / meta-analysis / 高质量会议；优先变量可被系统观测；神经科学/实验室设备依赖已标记。
> - **可信度声明**：每一条均由上述 API 实际返回，并经 Crossref/Europe PMC 按 DOI 或精确题名二次核验（卷期页码见 `_citation_meta.json`）。中文关键词（反馈调节、自适应规划、动态调度、个性化规划、闭环控制、人在回路、个性化干预）已尝试，CNKI/万方无公开机检 API，未纳入中文库记录。
> - **噪声控制**：泛关键词（如 `adaptive planning`）在医学库返回大量无关文献，已改用精确题名 `TITLE:"..."` 与 `AUTH:` 组合核验后采纳。

---

## 一、GB/T 7714 编号引用清单

[1] LOCKE E A, LATHAM G P. Building a practically useful theory of goal setting and task motivation: A 35-year odyssey[J]. American Psychologist, 2002, 57(9): 705-717. DOI:10.1037/0003-066x.57.9.705.

[2] LOCKE E A, LATHAM G P. New directions in goal-setting theory[J]. Current Directions in Psychological Science, 2006, 15(5): 265-268. DOI:10.1111/j.1467-8721.2006.00449.x.

[3] CARVER C S, SCHEIER M F. Control theory: A useful conceptual framework for personality-social, clinical, and health psychology[J]. Psychological Bulletin, 1982, 92(1): 111-135. DOI:10.1037/0033-2909.92.1.111.

[4] WROSCH C, SCHEIER M F, MILLER G E, et al. Adaptive self-regulation of unattainable goals: Goal disengagement, goal reengagement, and subjective well-being[J]. Personality and Social Psychology Bulletin, 2003, 29(12): 1494-1508. DOI:10.1177/0146167203256921.

[5] BANDURA A. Social cognitive theory of self-regulation[J]. Organizational Behavior and Human Decision Processes, 1991, 50(2): 248-287. DOI:10.1016/0749-5978(91)90022-l.

[6] KLUGER A N, DENISI A. The effects of feedback interventions on performance: A historical review, a meta-analysis, and a preliminary feedback intervention theory[J]. Psychological Bulletin, 1996, 119(2): 254-284. DOI:10.1037/0033-2909.119.2.254.

[7] HATTIE J, TIMPERLEY H. The power of feedback[J]. Review of Educational Research, 2007, 77(1): 81-112. DOI:10.3102/003465430298487.

[8] SHUTE V J. Focus on formative feedback[J]. Review of Educational Research, 2008, 78(1): 153-189. DOI:10.3102/0034654307313795.

[9] WINSTEIN C J, SCHMIDT R A. Reduced frequency of knowledge of results enhances motor skill learning[J]. Journal of Experimental Psychology: Learning, Memory, and Cognition, 1990, 16(4): 677-691. DOI:10.1037/0278-7393.16.4.677.

[10] HEBERT E P, COKER C. Optimizing feedback frequency in motor learning: Self-controlled and moderate frequency KR enhance skill acquisition[J]. Perceptual and Motor Skills, 2021, 128(5): 2381-2397. DOI:10.1177/00315125211036413.

[11] MARRAFFINO M D, SCHROEDER B L, FRAULINI N W, et al. Adapting training in real time: An empirical test of adaptive difficulty schedules[J]. Military Psychology, 2021, 33(3): 136-151. DOI:10.1080/08995605.2021.1897451.

[12] NAHUM-SHANI I, SMITH S N, SPRING B J, et al. Just-in-time adaptive interventions (JITAIs) in mobile health: Key components and design principles for ongoing health behavior support[J]. Annals of Behavioral Medicine, 2018, 52(6): 446-462. DOI:10.1007/s12160-016-9830-8.

[13] KLASNJA P, HEKLER E B, SHIFFMAN S, et al. Microrandomized trials: An experimental design for developing just-in-time adaptive interventions[J]. Health Psychology, 2015, 34(Suppl): 1220-1228. DOI:10.1037/hea0000305.

[14] NAHUM-SHANI I, QIAN M, ALMIRALL D, et al. Q-learning: A data analysis method for constructing adaptive interventions[J]. Psychological Methods, 2012, 17(4): 478-494. DOI:10.1037/a0029373.

[15] NAHUM-SHANI I, QIAN M, ALMIRALL D, et al. Experimental design and primary data analysis methods for comparing adaptive interventions[J]. Psychological Methods, 2012, 17(4): 457-477. DOI:10.1037/a0029372.

[16] MURPHY S A. An experimental design for the development of adaptive treatment strategies[J]. Statistics in Medicine, 2005, 24(10): 1455-1481. DOI:10.1002/sim.2022.

[17] COLLINS L M, MURPHY S A, BIERMAN K L. A conceptual framework for adaptive preventive interventions[J]. Prevention Science, 2004, 5(3): 185-196. DOI:10.1023/b:prev.0000037641.26017.00.

[18] CHAKRABORTY B, MURPHY S A. Dynamic treatment regimes[J]. Annual Review of Statistics and Its Application, 2014, 1(1): 447-464. DOI:10.1146/annurev-statistics-022513-115553.

[19] COLLINS L M, MURPHY S A, STRECHER V. The multiphase optimization strategy (MOST) and the sequential multiple assignment randomized trial (SMART)[J]. American Journal of Preventive Medicine, 2007, 32(5): S112-S118. DOI:10.1016/j.amepre.2007.01.022.

[20] MICHIE S, VAN STRALEN M M, WEST R. The behaviour change wheel: A new method for characterising and designing behaviour change interventions[J]. Implementation Science, 2011, 6(1): 42. DOI:10.1186/1748-5908-6-42.

[21] MICHIE S, RICHARDSON M, JOHNSTON M, et al. The behavior change technique taxonomy (v1) of 93 hierarchically clustered techniques[J]. Annals of Behavioral Medicine, 2013, 46(1): 81-95. DOI:10.1007/s12160-013-9486-6.

[22] KWASNICKA D, DOMBROWSKI S U, WHITE M, et al. Theoretical explanations for maintenance of behaviour change: A systematic review of behaviour theories[J]. Health Psychology Review, 2016, 10(3): 277-296. DOI:10.1080/17437199.2016.1151372.

[23] DALLERY J, CASSIDY R N, RAIFF B R. Single-case experimental designs to evaluate novel technology-based health interventions[J]. Journal of Medical Internet Research, 2013, 15(2): e22. DOI:10.2196/jmir.2227.

[24] OUELHADJ D, PETROVIC S. A survey of dynamic scheduling in manufacturing systems[J]. Journal of Scheduling, 2009, 12(4): 417-431. DOI:10.1007/s10951-008-0090-8.

[25] VIEIRA G E, HERRMANN J W, LIN E. Rescheduling manufacturing systems: A framework of strategies, policies, and methods[J]. Journal of Scheduling, 2003, 6(1): 39-62. DOI:10.1023/a:1022235519958.

[26] MORARI M, LEE J H. Model predictive control: Past, present and future[J]. Computers & Chemical Engineering, 1999, 23(4-5): 667-682. DOI:10.1016/s0098-1354(98)00301-9.

[27] BERTSIMAS D, SIM M. The price of robustness[J]. Operations Research, 2004, 52(1): 35-53. DOI:10.1287/opre.1030.0065.

[28] GEREVINI A E, SERINA I. Efficient plan adaptation through replanning windows and heuristic goals[J]. Fundamenta Informaticae, 2010, 102(3-4): 287-323. DOI:10.3233/fi-2010-309.

[29] AMERSHI S, CAKMAK M, KNOX W B, et al. Power to the people: The role of humans in interactive machine learning[J]. AI Magazine, 2014, 35(4): 105-120. DOI:10.1609/aimag.v35i4.2513.

[30] HORVITZ E. Principles of mixed-initiative user interfaces[C]//Proceedings of the SIGCHI Conference on Human Factors in Computing Systems (CHI '99). New York: ACM, 1999: 159-166. DOI:10.1145/302979.303030.

[31] KAMIKOKURYO K, HAGA T, VENTURE G, et al. Adversarial autoencoder and multi-armed bandit for dynamic difficulty adjustment in immersive virtual reality for rehabilitation[J]. Sensors, 2022, 22(12): 4499. DOI:10.3390/s22124499.

---

## 二、逐条源链接（DOI，均可解析）

| # | 标题 | 源链接 |
|---|------|--------|
| 1 | Goal setting and task motivation: 35-year odyssey | https://doi.org/10.1037/0003-066x.57.9.705 |
| 2 | New directions in goal-setting theory | https://doi.org/10.1111/j.1467-8721.2006.00449.x |
| 3 | Control theory (Carver & Scheier) | https://doi.org/10.1037/0033-2909.92.1.111 |
| 4 | Adaptive self-regulation of unattainable goals | https://doi.org/10.1177/0146167203256921 |
| 5 | Social cognitive theory of self-regulation | https://doi.org/10.1016/0749-5978(91)90022-l |
| 6 | Feedback interventions: meta-analysis | https://doi.org/10.1037/0033-2909.119.2.254 |
| 7 | The power of feedback | https://doi.org/10.3102/003465430298487 |
| 8 | Focus on formative feedback | https://doi.org/10.3102/0034654307313795 |
| 9 | Reduced KR frequency enhances learning | https://doi.org/10.1037/0278-7393.16.4.677 |
| 10 | Optimizing feedback frequency | https://doi.org/10.1177/00315125211036413 |
| 11 | Adaptive difficulty schedules | https://doi.org/10.1080/08995605.2021.1897451 |
| 12 | JITAI: key components & design principles | https://doi.org/10.1007/s12160-016-9830-8 |
| 13 | Microrandomized trials | https://doi.org/10.1037/hea0000305 |
| 14 | Q-learning for adaptive interventions | https://doi.org/10.1037/a0029373 |
| 15 | SMART: design & analysis | https://doi.org/10.1037/a0029372 |
| 16 | Experimental design for adaptive strategies | https://doi.org/10.1002/sim.2022 |
| 17 | Conceptual framework for adaptive interventions | https://doi.org/10.1023/b:prev.0000037641.26017.00 |
| 18 | Dynamic treatment regimes | https://doi.org/10.1146/annurev-statistics-022513-115553 |
| 19 | MOST & SMART | https://doi.org/10.1016/j.amepre.2007.01.022 |
| 20 | Behaviour change wheel | https://doi.org/10.1186/1748-5908-6-42 |
| 21 | Behavior change technique taxonomy v1 | https://doi.org/10.1007/s12160-013-9486-6 |
| 22 | Maintenance of behaviour change | https://doi.org/10.1080/17437199.2016.1151372 |
| 23 | Single-case experimental designs | https://doi.org/10.2196/jmir.2227 |
| 24 | Dynamic scheduling in manufacturing | https://doi.org/10.1007/s10951-008-0090-8 |
| 25 | Rescheduling framework | https://doi.org/10.1023/a:1022235519958 |
| 26 | Model predictive control | https://doi.org/10.1016/s0098-1354(98)00301-9 |
| 27 | The price of robustness | https://doi.org/10.1287/opre.1030.0065 |
| 28 | Plan adaptation / replanning windows | https://doi.org/10.3233/fi-2010-309 |
| 29 | Interactive machine learning | https://doi.org/10.1609/aimag.v35i4.2513 |
| 30 | Mixed-initiative user interfaces | https://doi.org/10.1145/302979.303030 |
| 31 | Bandit-based dynamic difficulty adjustment | https://doi.org/10.3390/s22124499 |

---

## 三、逐篇分析模板

> 本项目闭环：`Plan → Execution → Feedback → State Estimation → Adjustment → New Plan`，含 Review Scheduler、Replanning（per-user 冷却）、User Model Update、Duration Predictor、LLM Harness。

### [1] Locke & Latham (2002) — 目标设定理论 35 年
- **研究问题**：目标如何影响动机与绩效？机制与边界条件是什么？
- **核心理论**：Goal-Setting Theory：具体且有难度的目标提升绩效；目标通过努力、持久性、策略、注意聚焦起作用。
- **IV**：目标具体性、目标难度、反馈、承诺、任务复杂性。
- **DV**：任务绩效、满意度。
- **主要结论**：具体困难目标 > "尽力而为"；反馈是目标生效的必要条件；任务复杂时需学习目标。
- **证据强度**：强（35 年实验证据综述，外推性好）。
- **研究局限**：多为短期实验与简单任务；复杂任务调节强。
- **与本项目关系**：Goal → 任务时，目标难度与反馈需匹配；长期目标应拆为学习子目标。
- **可支持的系统设计**：目标设定器输出"难度系数 + 反馈计划"；LLM 生成 goals 时受难度规则约束。
- **可采集数据**：目标难度评分、承诺度、绩效。
- **可形成 User State**：`goal_difficulty`、`goal_commitment`、`current_goal_progress`。
- **Rule/Model/LLM 定位**：Rule（难度上下限）+ LLM Harness（生成候选目标）。
- **推荐优先级**：★★★★★。

### [2] Locke & Latham (2006) — 目标设定理论新方向
- **研究问题**：目标设定研究的新进展与机制澄清。
- **核心理论**：学习目标 vs 绩效目标；目标作为激励→绩效的中介。
- **IV**：目标类型、任务阶段。
- **DV**：绩效、策略使用。
- **主要结论**：复杂任务早期应设"学习目标"；目标与满意度通过绩效中介。
- **证据强度**：中—强（综述）。
- **局限**：叙述性综述。
- **与本项目关系**：新任务初期不应直接设高绩效目标，应设学习/探索目标。
- **系统设计**：任务阶段感知（新手/熟练）动态切换目标类型。
- **可采集数据**：任务阶段、绩效轨迹。
- **User State**：`task_stage`。
- **定位**：Rule。
- **优先级**：★★★★。

### [3] Carver & Scheier (1982) — 控制论框架
- **研究问题**：控制系统模型能否统一解释人格、临床与健康行为？
- **核心理论**：控制论/负反馈环（TOTE）：当前状态与目标比较，差异驱动行为；进展速率影响情感。
- **IV**：目标—现状差异、进展速率。
- **DV**：行为努力、情感（积极/消极）。
- **主要结论**：系统持续监控差异并调整行为；差异缩小快→积极情感，受阻→消极情感。
- **证据强度**：中—强（理论框架+既有证据整合）。
- **局限**：概念性，缺直接因果实验。
- **与本项目关系**：**闭环系统的理论骨架**——状态估计→差异→调整；情感/动机可作为调整信号。
- **系统设计**：定义 `discrepancy = goal - current_state`，并据此触发 Adjustment；引入进展速率作为用户情绪代理。
- **可采集数据**：目标进度、完成速率、自评情绪。
- **User State**：`goal_discrepancy`、`progress_rate`、`affect_signal`。
- **定位**：Rule（闭环触发）+ Statistical Model（进展建模）。
- **优先级**：★★★★★。

### [4] Wrosch et al. (2003) — 目标脱离与再投入
- **研究问题**：放弃不可达目标并投入新目标与主观幸福感的关系。
- **核心理论**：自适应自我调节：目标脱离（disengagement）与目标再投入（reengagement）。
- **IV**：脱离能力、再投入能力。
- **DV**：主观幸福感。
- **主要结论**：能脱离不可达目标并再投入者幸福感更高；两者有交互。
- **证据强度**：中（3 项相关研究，非实验）。
- **局限**：相关设计；自评结局。
- **与本项目关系**：系统需支持"合理放弃/重规划"，而非无限加压；长期目标冲突时应允许降级/替换。
- **系统设计**：Replanning 除"加任务"外提供"降级/放弃/替换目标"选项。
- **可采集数据**：目标达成率、放弃事件、后续再投入。
- **User State**：`disengagement_capacity`、`goal_abandon_events`。
- **定位**：Rule（连续失败触发降级）。
- **优先级**：★★★★。

### [5] Bandura (1991) — 自我调节的社会认知理论
- **研究问题**：自我调节的机制（自我监控、自我判断、自我反应）及自我效能作用。
- **核心理论**：Social Cognitive Theory：self-monitoring → self-judgment → self-reaction；反馈与自我效能影响坚持。
- **IV**：目标、自我效能、反馈、归因。
- **DV**：行为坚持、绩效、情绪反应。
- **主要结论**：自我监控与反馈是自我调节核心；自我效能调节目标坚持。
- **证据强度**：中—强（理论整合，大量实证支撑）。
- **局限**：理论性；变量测量多样。
- **与本项目关系**：User Model 应含自我效能与监控行为，用于调节反馈强度。
- **系统设计**：低自我效能用户降低难度上调幅度、增加正向反馈。
- **可采集数据**：自评效能、坚持时长、放弃点。
- **User State**：`self_efficacy`、`self_monitoring_level`。
- **定位**：ML（状态估计）+ LLM Harness（反馈话术）。
- **优先级**：★★★★。

### [6] Kluger & DeNisi (1996) — 反馈干预元分析
- **研究问题**：反馈干预对绩效的平均效应及负效应比例。
- **核心理论**：Feedback Intervention Theory（FIT）：反馈将注意指向任务/自我等不同层级，效果不同。
- **IV**：反馈类型、层级（任务/任务学习/自我）、呈现方式。
- **DV**：绩效。
- **主要结论**：平均 d≈0.4，但 **超过 1/3 的反馈干预降低绩效**；指向"自我"的反馈最易有害。
- **证据强度**：强（607 个效应量元分析，经典）。
- **局限**：年代较早；调节变量复杂。
- **与本项目关系**：**警示**——反馈不是越多越好；频繁负反馈可能损害表现。与"避免系统震荡"直接相关。
- **系统设计**：反馈指向任务与策略，避免评价用户人格；负反馈伴随可操作建议；设置反馈频率上限。
- **可采集数据**：反馈类型、频率、后续绩效变化。
- **User State**：`feedback_sensitivity`、`negative_feedback_ratio`。
- **定位**：Rule（反馈策略约束）+ LLM Harness（措辞）。
- **优先级**：★★★★★。

### [7] Hattie & Timperley (2007) — 反馈的力量
- **研究问题**：反馈为何有效/无效？如何设计有效反馈？
- **核心理论**：反馈三问：Where am I going? How am I going? Where to next?（feed up/back/forward）。
- **IV**：反馈类型与层级（任务/过程/自我调节/自我）。
- **DV**：学习与成就。
- **主要结论**：反馈是强影响因素，但类型/方式决定正负；过程与自我调节层级的反馈最有效。
- **证据强度**：强（大型证据综述，引用极高）。
- **局限**：教育场景为主；效应量异质。
- **与本项目关系**：定义反馈内容模板（目标—现状—下一步），直接用于执行反馈设计。
- **系统设计**：每次反馈包含"目标对照 + 差距原因 + 下一步调整"三要素。
- **可采集数据**：反馈类型与用户响应。
- **User State**：`feedback_effectiveness`。
- **定位**：LLM Harness（生成结构化反馈）+ Rule。
- **优先级**：★★★★★。

### [8] Shute (2008) — 形成性反馈
- **研究问题**：形成性反馈的类型、时机与效果调节因素，及设计指南。
- **核心理论**：Formative feedback：非评价、支持性、及时、具体。
- **IV**：反馈类型（验证/解释/提示/示例）、时机（即时/延迟）、学习者特征、任务。
- **DV**：学习改进。
- **主要结论**：复杂任务宜延迟反馈，简单任务宜即时；反馈需具体且指向改进；个体差异调节效果。
- **证据强度**：中—强（系统综述）。
- **局限**：结论多为定性综合。
- **与本项目关系**：决定反馈时点（复杂任务不打断心流、延迟汇总）。
- **系统设计**：按任务复杂度选择即时/延迟反馈；复杂任务在阶段结束后汇总。
- **可采集数据**：反馈时机、任务复杂度、改进量。
- **User State**：`feedback_timing_pref`。
- **定位**：Rule + Statistical Model。
- **优先级**：★★★★★。

### [9] Winstein & Schmidt (1990) — 降低反馈频率促进运动学习
- **研究问题**：降低结果知识（KR）频率是否优于 100% 反馈？
- **核心理论**：反馈频率与"指导性假设"；过度反馈导致依赖，损害保持/迁移。
- **IV**：KR 频率（100% vs 降低，如 50%）。
- **DV**：运动技能习得与保持/迁移。
- **主要结论**：降低 KR 频率提升学习与保持（尽管习得期表现略低）。
- **证据强度**：强（经典受控实验，多次复现；运动学习领域）。
- **局限**：运动任务，迁移到认知任务需谨慎。
- **与本项目关系**：**反馈频率的核心证据**——不必每次执行都给反馈，避免用户依赖系统。
- **系统设计**：反馈频率可调（每次/每 N 次/仅异常时），默认中等频率。
- **可采集数据**：反馈频率、独立完成率。
- **User State**：`scaffold_dependency`。
- **定位**：Rule（频率策略）。
- **优先级**：★★★★★。

### [10] Hebert & Coker (2021) — 优化反馈频率
- **研究问题**：不同 KR 频率（0/50/100%/自控）对技能习得与保持的影响。
- **核心理论**：最优反馈频率；自控反馈。
- **IV**：KR 频率条件。
- **DV**：习得与保持表现。
- **主要结论**：中等频率与自控反馈优于 100% 与 0%；自控反馈效果好。
- **证据强度**：中—强（实验，样本中等）。
- **局限**：单一运动任务；短期。
- **与本项目关系**：支持"用户可自主请求反馈 + 系统默认中等频率"。
- **系统设计**：提供"请求提示/反馈"按钮，同时系统按中等频率主动反馈。
- **可采集数据**：主动请求反馈次数、频率设置。
- **User State**：`feedback_request_rate`。
- **定位**：Rule + 交互设计。
- **优先级**：★★★★。

### [11] Marraffino et al. (2021) — 实时自适应难度排程实证
- **研究问题**：自适应难度排程（基于表现实时调整难度）对训练效果的影响。
- **核心理论**：自适应难度/desirable difficulty；表现—难度匹配。
- **IV**：难度排程策略（自适应 vs 固定）。
- **DV**：训练/保持表现、感知难度。
- **主要结论**：自适应难度可维持适当挑战水平；策略细节影响保持。
- **证据强度**：中（实证，军事训练场景，样本有限）。
- **局限**：特定任务；效应量中等。
- **与本项目关系**：直接对应"下一阶段任务难度如何调整"。
- **系统设计**：根据最近完成率/时长动态调整任务难度与数量。
- **可采集数据**：完成率、时长、难度变化。
- **User State**：`performance_trend`、`difficulty_level`。
- **定位**：Rule + Statistical Model。
- **优先级**：★★★★★。

### [12] Nahum-Shani et al. (2018) — JITAI 关键组件与设计原则
- **研究问题**：如何在恰当时间提供恰当类型/剂量的干预，并适应个体变化状态？
- **核心理论**：Just-in-Time Adaptive Intervention（JITAI）；tailoring variables、decision points、decision rules、intervention options；状态（availability、receptivity）。
- **IV**：干预组件、决策规则、触发时机。
- **DV**：目标行为（健康行为）及中介状态。
- **主要结论**：提出 JITAI 组件化设计语言；强调"状态变化"与"适时性"是核心，反对静态干预。
- **证据强度**：强（领域奠基性框架综述，引用极高）。
- **局限**：框架性，具体参数需实证。
- **与本项目关系**：**闭环反馈调节的直接框架**——定义决策点、状态、决策规则。
- **系统设计**：明确 decision points（任务完成/每日/每周）、tailoring variables（完成率、时长、情绪）、decision rules。
- **可采集数据**：状态变量、触发时点、干预剂量、响应。
- **User State**：`availability`、`receptivity`、`context_state`。
- **定位**：Rule（决策规则）+ ML（个体化规则学习）。
- **优先级**：★★★★★（必读）。

### [13] Klasnja et al. (2015) — 微随机试验（MRT）
- **研究问题**：如何实验性地评估 JITAI 组件的即时因果效应与时变调节？
- **核心理论**：Micro-randomized Trial：在每个决策点随机化干预组件。
- **IV**：决策点随机分配的干预组件。
- **DV**： proximal（近端）效果、时变调节效应。
- **主要结论**：MRT 可估计因果效应，支持"何时/对谁/何种组件有效"。
- **证据强度**：强（方法学论文，已在 mHealth 广泛采用）。
- **局限**：成本高、需足够决策点；依从性挑战。
- **与本项目关系**：为"反馈频率/调整策略"提供在线实验设计，避免凭直觉调参。
- **系统设计**：在 decision points 做随机化 A/B（如是否提示、反馈形式），持续学习最优策略。
- **可采集数据**：随机分配、近端结果、时变协变量。
- **User State**：`treatment_effect_estimate`。
- **定位**：ML（因果/在线学习）+ 实验基础设施。
- **优先级**：★★★★★。

### [14] Nahum-Shani et al. (2012) — Q-learning 构建自适应干预
- **研究问题**：如何从 SMART 数据估计最优决策规则序列？
- **核心理论**：Q-learning（回归推广到序贯决策）；用 SMART 数据估计最优干预序列。
- **IV**：各阶段干预选项、协变量。
- **DV**：最优决策规则与长期结局。
- **主要结论**：Q-learning 能构建比设计内嵌规则更深的个体化决策规则；优于传统方法。
- **证据强度**：中—强（方法学+真实 SMART 案例）。
- **局限**：依赖模型设定；样本量要求大。
- **与本项目关系**：Replanning 策略可用 Q-learning 从历史反馈中学习（何时调整、调整多少）。
- **系统设计**：以 `state(用户特征/近期表现) → action(调整类型) → reward(完成/保持)` 建模；先离线学习，后在线微调。
- **可采集数据**：状态、动作、奖励序列。
- **User State**：`policy_state_vector`。
- **定位**：ML（强化学习）。
- **优先级**：★★★★（中期引入）。

### [15] Nahum-Shani et al. (2012) — 比较自适应干预的实验设计与分析
- **研究问题**：如何设计 SMART 以比较高品质自适应干预并做主要分析？
- **核心理论**：SMART；决策规则；与固定干预设计的比较。
- **IV**：SMART 设计因素。
- **DV**：主要研究问题的结局。
- **主要结论**：SMART 可回答"序贯决策"问题，优于传统 RCT；给出分析方法。
- **证据强度**：强（方法学）。
- **局限**：设计复杂；样本量需求高。
- **与本项目关系**：为闭环策略的评估提供实验设计范式。
- **系统设计**：分阶段 rollout（先固定策略，再自适应），记录决策规则。
- **可采集数据**：阶段、规则版本、结局。
- **User State**：`experiment_arm`。
- **定位**：实验/评估设计。
- **优先级**：★★★★。

### [16] Murphy (2005) — 自适应治疗策略的实验设计
- **研究问题**：如何设计试验以开发"随个体反应反复调整"的治疗策略？
- **核心理论**：Sequential Multiple Assignment Randomized Trial（SMART）的最早系统提出之一。
- **IV**：阶段化随机分配。
- **DV**：长期结局。
- **主要结论**：提出 SMART 设计、样本量与分析方法，解决延迟效应问题。
- **证据强度**：强（奠基方法学论文）。
- **局限**：理论性；实现成本。
- **与本项目关系**：Replanning 规则设计的历史方法论源头。
- **系统设计**：多阶段调整规则的分层验证。
- **可采集数据**：阶段反应、再分配。
- **User State**：`stage_response_history`。
- **定位**：实验设计。
- **优先级**：★★★★。

### [17] Collins et al. (2004) — 自适应预防干预概念框架
- **研究问题**：自适应干预的概念、设计与评估原则。
- **核心理论**：tailoring variables（定制变量）+ 预设决策规则；按需分配剂量。
- **IV**：定制变量、剂量决策规则。
- **DV**：干预效果。
- **主要结论**：自适应干预应按个体特征与随时间变化的需求调整剂量；决策规则需预设。
- **证据强度**：中—强（概念框架，广泛引用）。
- **局限**：概念性。
- **与本项目关系**：提供"何时调整 + 依据什么变量"的框架。
- **系统设计**：定义 tailoring variables（近期完成率、时长偏差、情绪）与剂量规则。
- **可采集数据**：定制变量、剂量、结局。
- **User State**：`tailoring_variables`。
- **定位**：Rule。
- **优先级**：★★★★★。

### [18] Chakraborty & Murphy (2014) — 动态治疗方案（DTR）综述
- **研究问题**：DTR 的构造、估计与推断方法综述。
- **核心理论**：Dynamic Treatment Regime = 每阶段一条决策规则；个性化医疗核心工具。
- **IV**：SMART 设计、Q-learning、边际结构模型。
- **DV**：最优决策规则与结局。
- **主要结论**：统计方法（Q-learning/MSM）可从数据构建循证 DTR，并处理非标准渐近。
- **证据强度**：强（权威综述）。
- **局限**：统计复杂性；软件/实现门槛。
- **与本项目关系**：Replanning 策略学习的方法论总览与选型依据。
- **系统设计**：选用 Q-learning 或 MSM 构建 per-user 调整规则；保留策略版本。
- **可采集数据**：阶段数据、协变量、结局。
- **User State**：`regime_version`。
- **定位**：ML/统计。
- **优先级**：★★★★。

### [19] Collins et al. (2007) — MOST 与 SMART
- **研究问题**：如何用 MOST/SMART 构建更高效、可扩展的干预？
- **核心理论**：Multiphase Optimization Strategy + SMART。
- **IV**：干预组件、优化策略。
- **DV**：干预效果与效率。
- **主要结论**：先用因子实验优化组件，再用 SMART 构建自适应规则，比"整体打包 RCT"更高效。
- **证据强度**：中—强（方法学综述）。
- **局限**：方法性。
- **与本项目关系**：指导系统"先优化单个反馈/计划组件，再组合成自适应策略"。
- **系统设计**：分阶段上线组件（反馈形式、难度调整），避免一次性全量自适应。
- **可采集数据**：组件级效果。
- **User State**：`component_effect_map`。
- **定位**：实验设计。
- **优先级**：★★★★。

### [20] Michie et al. (2011) — 行为改变轮（BCW）
- **研究问题**：如何系统描述并设计行为改变干预？
- **核心理论**：COM-B（Capability, Opportunity, Motivation → Behavior）；9 类干预功能、7 类政策。
- **IV**：干预功能、行为来源。
- **DV**：行为改变。
- **主要结论**：提供可操作的行为诊断与干预选择框架；可靠性经验证。
- **证据强度**：强（系统框架开发+可靠性检验，引用极高）。
- **局限**：框架性；效果依赖实施。
- **与本项目关系**：当用户反馈差时，诊断是能力/机会/动机问题，再选择干预（任务调整 vs 提醒 vs 激励）。
- **系统设计**：Adjustment 依据 COM-B 分类选择策略（难度、提醒、激励），而非只调任务量。
- **可采集数据**：行为诊断标签、干预选择、行为变化。
- **User State**：`capability`、`opportunity`、`motivation`。
- **定位**：Rule（策略映射）+ LLM Harness（诊断文本）。
- **优先级**：★★★★★。

### [21] Michie et al. (2013) — 行为改变技术分类 v1（93 项）
- **研究问题**：建立标准化的行为改变技术（BCT）分类。
- **核心理论**：BCT Taxonomy v1（93 项，16 组）。
- **IV**：BCT 类型。
- **DV**：干预报告的一致性与可复制性。
- **主要结论**：提供共识性 BCT 标签，多数编码可靠性高。
- **证据强度**：强（国际共识+信度评估）。
- **局限**：分类学，不直接给效应量。
- **与本项目关系**：为系统内置"干预/激励动作库"提供标准化词汇。
- **系统设计**：把提醒、目标设定、反馈、自我监控等实现为带 BCT 标签的原子动作。
- **可采集数据**：BCT 动作使用频次与效果。
- **User State**：`bct_exposure`。
- **定位**：Rule（动作库）。
- **优先级**：★★★★。

### [22] Kwasnicka et al. (2016) — 行为改变维持的理论解释
- **研究问题**：哪些理论解释行为改变的长期维持？
- **核心理论**：维持涉及动机、自我调节、资源、习惯、环境/社会影响五主题。
- **IV**：理论（100 个）中的维持相关构念。
- **DV**：行为维持。
- **主要结论**：维持机制与启动机制不同；习惯与自我调节、资源是关键。
- **证据强度**：中—强（系统综述 100 个理论）。
- **局限**：理论综述；缺量化整合。
- **与本项目关系**：长期计划应关注习惯养成与资源管理，而非仅任务难度。
- **系统设计**：引入习惯型固定任务、资源耗尽检测与恢复安排。
- **可采集数据**：坚持时长、习惯强度代理、休息行为。
- **User State**：`habit_strength`、`resource_level`。
- **定位**：Rule + Statistical Model。
- **优先级**：★★★★。

### [23] Dallery et al. (2013) — 单被试实验设计评估技术干预
- **研究问题**：如何用单被试（n-of-1）设计评估新型技术干预的初步效力？
- **核心理论**：Single-case experimental design；时间序列；效果量。
- **IV**：干预/撤除（A-B-A 等）。
- **DV**：个体时间序列行为。
- **主要结论**：单被试设计适合快速评估技术干预，可分离活性成分并检验机制。
- **证据强度**：中—强（方法学综述）。
- **局限**：外部效度有限，需重复。
- **与本项目关系**：适合在真实用户上快速 A/B 测试反馈/调整策略（n-of-1）。
- **系统设计**：对个体启用"策略开关"序列并分析时间序列。
- **可采集数据**：个体时间序列（每日完成、情绪）。
- **User State**：`personal_effect_estimate`。
- **定位**：评估方法。
- **优先级**：★★★★。

### [24] Ouelhadj & Petrovic (2009) — 动态调度综述
- **研究问题**：制造系统中动态调度的类型、策略与方法。
- **核心理论**：完全反应式 / 预测—反应式调度；重调度策略。
- **IV**：干扰类型、调度策略。
- **DV**：调度性能、稳定性。
- **主要结论**：预测—反应式最常用；需权衡"性能"与"稳定性"；事件驱动 vs 周期驱动。
- **证据强度**：强（领域权威综述）。
- **局限**：制造场景，迁移需适配。
- **与本项目关系**：**何时重新规划**与**避免震荡**的直接理论来源。
- **系统设计**：采用预测—反应式：保持基础计划，仅在关键事件或周期触发重规划；度量 schedule stability。
- **可采集数据**：干扰事件、重规划频率、计划变更幅度。
- **User State**：`schedule_stability`、`disruption_events`。
- **定位**：Rule（触发策略）。
- **优先级**：★★★★★。

### [25] Vieira et al. (2003) — 重调度框架
- **研究问题**：重调度的策略、政策与方法应如何分类与选择？
- **核心理论**：Rescheduling framework：何时重调度（policy）、如何重调度（method）、策略（periodic/event-driven）。
- **IV**：重调度触发策略、方法、扰动程度。
- **DV**：性能与计划稳定性。
- **主要结论**：事件驱动与周期驱动各有适用；局部修复优于全面重排以保稳定。
- **证据强度**：强（框架综述，引用高）。
- **局限**：概念框架，参数依场景。
- **与本项目关系**：Replanning 冷却与"局部调整优先"设计依据。
- **系统设计**：默认局部修复（调整单任务），仅重大偏差才全量重规划。
- **可采集数据**：重规划触发原因、变更范围。
- **User State**：`replan_scope`、`replan_trigger_reason`。
- **定位**：Rule。
- **优先级**：★★★★★。

### [26] Morari & Lee (1999) — 模型预测控制（MPC）
- **研究问题**：MPC 的原理、历史与未来方向。
- **核心理论**：滚动时域优化（receding horizon）：基于模型预测未来，仅执行第一步，再重新优化；含约束。
- **IV**：预测时域、控制时域、约束、权重。
- **DV**：控制性能、稳定性。
- **主要结论**：MPC 能处理约束与多变量问题；时域/权重决定激进程度。
- **证据强度**：强（权威综述，引用极高）。
- **局限**：需模型；计算成本。
- **与本项目关系**：**如何重规划而不震荡**的工程范式——滚动优化+只执行一步+约束/权重抑制过大调整。
- **系统设计**：每次只调整近期任务（滚动时域），加入"调整幅度上限"与"冷却"约束。
- **可采集数据**：预测误差、调整幅度、稳定性。
- **User State**：`control_horizon`、`adjustment_magnitude`。
- **定位**：Rule（约束）+ Statistical Model（模型预测）。
- **优先级**：★★★★★。

### [27] Bertsimas & Sim (2004) — 鲁棒优化与价格
- **研究问题**：如何在数据不确定下获得不过度保守的鲁棒解？
- **核心理论**：Robust Optimization；budget of uncertainty（Γ）控制保守度。
- **IV**：不确定性预算 Γ、参数不确定性。
- **DV**：目标值、可行性/违反概率。
- **主要结论**：通过调节 Γ 在"性能"与"鲁棒性"间权衡；可得线性可解形式。
- **证据强度**：强（Operations Research 经典，理论+实验）。
- **局限**：静态优化；分布假设。
- **与本项目关系**：应对用户时长/完成率不确定性——不要按最坏情况过度排计划。
- **系统设计**：Duration Predictor 输出区间而非点估计；计划留 buffer，Γ 控制缓冲量。
- **可采集数据**：时长预测误差、违反预算次数。
- **User State**：`uncertainty_budget`、`time_prediction_error`。
- **定位**：Statistical Model / 优化。
- **优先级**：★★★★。

### [28] Gerevini & Serina (2010) — 重规划窗口与启发式目标做计划修复
- **研究问题**：如何在计划失效时高效地局部修复而非从头重规划？
- **核心理论**：Plan adaptation / replanning windows：定位受影响子计划，设启发式目标做局部重规划。
- **IV**：修复窗口大小、启发式目标。
- **DV**：修复质量与计算效率。
- **主要结论**：局部修复显著优于全量重规划；窗口选择影响效果。
- **证据强度**：中—强（算法论文+实验）。
- **局限**：经典规划设定；未含人类因素。
- **与本项目关系**：Replanning 应做"局部修复"，只重排受影响的任务段。
- **系统设计**：检测偏差影响的任务子图，仅对该窗口重生成任务。
- **可采集数据**：受影响任务范围、修复耗时。
- **User State**：`affected_subplan`。
- **定位**：Rule/算法（LLM Harness 仅生成窗口内候选）。
- **优先级**：★★★★。

### [29] Amershi et al. (2014) — 交互式机器学习中的人
- **研究问题**：人在交互式 ML 系统中的角色及对系统有效性的影响。
- **核心理论**：Interactive Machine Learning：人机紧耦合、快速迭代反馈。
- **IV**：交互设计、用户反馈。
- **DV**：系统学习效果与用户体验。
- **主要结论**：忽视用户会导致系统失败；紧耦合交互提升学习与体验。
- **证据强度**：中—强（案例研究+论述，AI Magazine）。
- **局限**：案例为主，非受控实验。
- **与本项目关系**：LLM Harness 与用户之间需持续交互闭环，反馈要能改变系统行为。
- **系统设计**：用户对计划/反馈的显式修正进入 User Model 与策略。
- **可采集数据**：用户修正、接受/拒绝建议。
- **User State**：`user_correction_history`。
- **定位**：LLM Harness 交互层。
- **优先级**：★★★★。

### [30] Horvitz (1999) — 混合主动式用户界面原则
- **研究问题**：系统何时应主动行动/询问，何时应等待？
- **核心理论**：Mixed-initiative；基于期望效用决定是否打断（考虑用户成本/收益）。
- **IV**：行动/询问的时机与不确定性。
- **DV**：用户效用、打断成本。
- **主要结论**：应基于效用模型决定是否介入，避免过度打扰；不确定时先询问。
- **证据强度**：中—强（经典 CHI 论文，框架+原型）。
- **局限**：早期工作；效用参数难估。
- **与本项目关系**：**何时提示/重规划**的判据——按收益-打扰成本决定，避免系统震荡与用户反感。
- **系统设计**：调整/提醒前计算期望效用；低收益高打扰时延后。
- **可采集数据**：介入时点、用户响应率、忽略率。
- **User State**：`interruption_cost`、`responsiveness`。
- **定位**：Rule（介入策略）+ Statistical Model（效用）。
- **优先级**：★★★★★。

### [31] Kamikokuryo et al. (2022) — 多臂老虎机做动态难度调整
- **研究问题**：用表示学习+多臂老虎机实时调整康复训练难度是否可行？
- **核心理论**：Adversarial Autoencoder（降维/状态表示）+ Multi-Armed Bandit（奖励驱动难度选择）。
- **IV**：bandit 算法（Boltzmann / Sibling Kalman）、表示方式。
- **DV**：累积加权概率误差（跟踪能力演化的效果）。
- **主要结论**：MAB 能快速学习能力演化并调整难度；Sibling Kalman 优于 Boltzmann。
- **证据强度**：中（初步研究，N 小，VR/传感器场景）。
- **局限**：**依赖 VR/动作捕捉设备**；样本小；康复场景。
- **与本项目关系**：展示"bandit + 表示学习"做难度自适应的可行路径（可迁移到行为数据）。
- **系统设计**：以 bandit 在多个难度/任务间探索利用，奖励=完成率与保持。
- **可采集数据**：任务结果作为奖励、难度选择历史。
- **User State**：`ability_latent`、`bandit_state`。
- **定位**：ML（bandit）。
- **优先级**：★★★（方法参考，去设备化后可用）。

---

## 附：方向9 检索方法学备注
- API 调用保存原始 JSON 于 `./api/`；`_verified_titles_epmc.json` 记录精确题名→返回的核验过程，`_citation_meta.json` 记录 Crossref 卷期页码/类型。
- 曾误配的题名已剔除（如"Dynamic treatment regimes"精确检索命中 2026 年无关论文、"The power of feedback"命中自行车运动反馈研究），改用 `query.author` + `query.container-title` 约束后取得正确记录（见 [18][7]）。
- 未采纳但可关注：`10.1177/2161783x251414444`（Flow Optimizer 动态难度框架，2026）、`10.1016/j.jvoice.2023.04.006`（反馈频率在嗓音运动学习）。
- 与本项目最直接相关的三组：**(A) JITAI/DTR 组 [12-19]** 提供闭环决策规则与在线实验设计；**(B) 动态调度/控制组 [24-28]** 提供重规划触发、局部修复、MPC 滚动优化与鲁棒缓冲；**(C) 反馈设计组 [6-11]** 提供反馈频率与内容的具体边界条件。
