# 方向4：任务耗时 / 人类表现预测（Task Duration & Human Performance Prediction）

**检索 2104 篇，采纳 39 篇**：本方向实际执行关键词检索 56 组（Crossref REST API 56 组 + Europe PMC REST API 56 组，部分查询重叠；另有 7 组 arXiv API 查询因接口返回 HTTP 406 未纳入），原始命中条目去重后 **2104 条**候选，按主题相关性打分并人工复核后采纳 **39 篇**。所有采纳文献的 DOI 均实际存在于本轮检索结果中，并逐条经 Crossref 核验。

- 检索渠道：Crossref REST API（题录 + DOI 校验）、Europe PMC REST API（题录 + 摘要，`resultType=core`）、Semantic Scholar Graph API（部分摘要补全）。原始数据保存在本目录 `api/`（`crossref_*.json`、`epmc_*.json`、`cr_*.txt`、`epmc_*.txt` 为各组原始命中；`candidates_04.json/.txt` 为去重候选；`ranked_04.txt` 为相关性排序；`selected_abstracts_04.txt` 与 `abstracts.json` 为采纳文献摘要；`verify/` 为 Crossref 元数据核验快照）。
- 筛选原则：优先 peer-reviewed 期刊、系统综述/元分析、高质量会议（CHI/CSCW/SIGCSE/LAK/CHI EA）与工程实证研究；优先变量可被系统观测（`theoretical_duration`、`historical_duration`、`task_type`、`user_skill`、`fatigue`、completion time、logs、self-report）；依赖 EEG/fMRI 或实验室设备者必须标记。
- 本项目背景对应：`Duration Predictor`（目标 `actual_duration`，特征 `theoretical_duration` / `historical_duration` / `task_type` / `user_skill` / `fatigue`）、RuleEngine、Scheduler、Task Generator、LLM Harness。本方向直接为「能否建立用户级耗时倍率」「简单统计模型还是 ML」提供依据。

---

## 一、采纳文献清单（GB/T 7714 引用格式）

### A. 时间预测偏差与规划谬误（耗时预测的偏差来源）

[1] BUEHLER R, GRIFFIN D, ROSS M. Exploring the "planning fallacy": why people underestimate their task completion times[J]. Journal of Personality and Social Psychology, 1994, 67(3): 366-381. DOI:10.1037/0022-3514.67.3.366.

[2] BUEHLER R, GRIFFIN D, PEETZ J. The planning fallacy[M]//ZANNA M P, OLSON J M. Advances in Experimental Social Psychology: Vol 43. San Diego: Academic Press, 2010: 1-62. DOI:10.1016/S0065-2601(10)43001-4.

[3] HALKJELSVIK T, JØRGENSEN M. From origami to software development: a review of studies on judgment-based predictions of performance time[J]. Psychological Bulletin, 2012, 138(2): 238-271. DOI:10.1037/a0025996.

[4] THOMAS K E, NEWSTEAD S E, HANDLEY S J. Exploring the time prediction process: the effects of task experience and complexity on prediction accuracy[J]. Applied Cognitive Psychology, 2003, 17(6): 655-673. DOI:10.1002/acp.893.

[5] GOSWAMI I, URMINSKY O. More time, more work: how time limits bias estimates of task scope and project duration[J]. Judgment and Decision Making, 2020, 15(6): 994-1008. DOI:10.1017/S1930297500008196.

[6] KOOLE S, VAN'T SPIJKER M. Overcoming the planning fallacy through willpower: effects of implementation intentions on actual and predicted task-completion times[J]. European Journal of Social Psychology, 2000, 30(6): 873-888. DOI:10.1002/1099-0992(200011/12)30:6<873::AID-EJSP22>3.0.CO;2-U.

[7] SPILLER S A, LYNCH J G. Individuals exhibit the planning fallacy for time but not for money[R/OL]. SSRN Working Paper, 2009. DOI:10.2139/ssrn.1458380.

[8] HALKJELSVIK T, JØRGENSEN M. Do people underestimate time? Exploring feedback-based performance time predictions using brief tasks[J]. Timing & Time Perception, 2026, 14(3): 282-307. DOI:10.1163/22134468-bja10136.

[9] QIAN B, ZHENG Q. An issue of public affairs management: the effect of time slack and need for cognition on prediction of task completion[J]. Public Personnel Management, 2012, 41(5): 1-8. DOI:10.1177/009102601204100501.

### B. 人类绩效建模与工程化预测（KLM / GOMS / Fitts）

[10] CARD S K, MORAN T P, NEWELL A. The keystroke-level model for user performance time with interactive systems[J]. Communications of the ACM, 1980, 23(7): 396-410. DOI:10.1145/358886.358895.

[11] JOHN B E, KIERAS D E. The GOMS family of user interface analysis techniques: comparison and contrast[J]. ACM Transactions on Computer-Human Interaction, 1996, 3(4): 320-351. DOI:10.1145/235833.236054.

[12] LUO L, JOHN B E. Predicting task execution time on handheld devices using the keystroke-level model[C]//CHI '05 Extended Abstracts on Human Factors in Computing Systems. New York: ACM, 2005: 1605-1608. DOI:10.1145/1056808.1056977.

[13] LEE S C, YOON S H, JI Y G. Modeling task completion time of in-vehicle information systems while driving with keystroke level modeling[J]. International Journal of Industrial Ergonomics, 2019, 72: 252-260. DOI:10.1016/j.ergon.2019.06.001.

[14] FITTS P M. The information capacity of the human motor system in controlling the amplitude of movement[J]. Journal of Experimental Psychology, 1954, 47(6): 381-391. DOI:10.1037/h0055392.

### C. 学习曲线、练习效应与技能获得

[15] NEWELL A, ROSENBLOOM P S. Mechanisms of skill acquisition and the law of practice[M]//ANDERSON J R. Cognitive Skills and Their Acquisition. London: Routledge, 2013: 12-66. DOI:10.4324/9780203728178-6.

[16] DONNER Y, HARDY J L. Piecewise power laws in individual learning curves[J]. Psychonomic Bulletin & Review, 2015, 22(5): 1308-1319. DOI:10.3758/s13423-015-0811-x.

[17] ERICSSON K A, KRAMPE R T, TESCH-RÖMER C. The role of deliberate practice in the acquisition of expert performance[J]. Psychological Review, 1993, 100(3): 363-406. DOI:10.1037/0033-295X.100.3.363.

[18] ERICSSON K A. Deliberate practice and acquisition of expert performance: a general overview[J]. Academic Emergency Medicine, 2008, 15(11): 988-994. DOI:10.1111/j.1553-2712.2008.00227.x.

### D. 个体差异（影响耗时的稳定个体因素）

[19] BIDERMAN M D, NGUYEN N T, SEBREN J. Time-on-task mediates the conscientiousness-performance relationship[J]. Personality and Individual Differences, 2008, 44(4): 887-897. DOI:10.1016/j.paid.2007.10.022.

[20] RATCLIFF R, THOMPSON C A, MCKOON G. Modeling individual differences in response time and accuracy in numeracy[J]. Cognition, 2015, 137: 115-136. DOI:10.1016/j.cognition.2014.12.004.

[21] PARASURAMAN R, JIANG Y. Individual differences in cognition, affect, and performance: behavioral, neuroimaging, and molecular genetic approaches[J]. NeuroImage, 2012, 59(1): 70-82. DOI:10.1016/j.neuroimage.2011.04.040.

### E. 时间-on-task 与学习数据（可观测的耗时代理）

[22] LEINONEN J, CASTRO F E V, HELLAS A. Time-on-Task metrics for predicting performance[C]//Proceedings of the 53rd ACM Technical Symposium on Computer Science Education. New York: ACM, 2022: 871-877. DOI:10.1145/3478431.3499359.

[23] LEINONEN J, CASTRO F E V, HELLAS A. Time-on-task metrics for predicting performance[J]. ACM Inroads, 2022, 13(2): 42-49. DOI:10.1145/3534564.

[24] NGUYEN Q. Rethinking time-on-task estimation with outlier detection accounting for individual, time, and task differences[C]//Proceedings of the Tenth International Conference on Learning Analytics & Knowledge. New York: ACM, 2020: 376-381. DOI:10.1145/3375462.3375538.

[25] PARK S. Analysis of time-on-task, behavior experiences, and performance in two online courses with different authentic learning tasks[J]. The International Review of Research in Open and Distributed Learning, 2017, 18(2). DOI:10.19173/irrodl.v18i2.2433.

[26] ROMERO M, BARBERÀ E. Quality of e-learners' time and learning performance beyond quantitative time-on-task[J]. The International Review of Research in Open and Distributed Learning, 2011, 12(5): 125. DOI:10.19173/irrodl.v12i5.999.

### F. 工作量估计：专家判断 vs 机器学习

[27] JØRGENSEN M. Practical guidelines for expert-judgment-based software effort estimation[J]. IEEE Software, 2005, 22(3): 57-63. DOI:10.1109/MS.2005.73.

[28] GRIMSTAD S, JØRGENSEN M. Inconsistency of expert judgment-based estimates of software development effort[J]. Journal of Systems and Software, 2007, 80(11): 1770-1777. DOI:10.1016/j.jss.2007.03.001.

[29] WEN J, LI S, LIN Z, et al. Systematic literature review of machine learning based software development effort estimation models[J]. Information and Software Technology, 2012, 54(1): 41-59. DOI:10.1016/j.infsof.2011.09.002.

[30] KOCAGUNELI E, MENZIES T, KEUNG J, et al. Active learning and effort estimation: finding the essential content of software effort estimation data[J]. IEEE Transactions on Software Engineering, 2013, 39(8): 1040-1053. DOI:10.1109/TSE.2012.88.

[31] SATAPATHY S M, RATH S K. Empirical assessment of machine learning models for agile software development effort estimation using story points[J]. Innovations in Systems and Software Engineering, 2017, 13(2-3): 191-200. DOI:10.1007/s11334-017-0288-z.

### G. 面向具体任务/系统的耗时预测（可迁移的 ML 设计）

[32] KAWAGUCHI S, OHSITA Y, KAWASHIMA M, et al. Task completion time prediction scaled by machine learning model uncertainty[C]//2024 20th International Conference on Network and Service Management (CNSM). New York: IEEE, 2024: 1-7. DOI:10.23919/CNSM62983.2024.10814629.

[33] HUANG C C, LAI J, CHO D Y, et al. A machine learning study to improve surgical case duration prediction[R/OL]. medRxiv Preprint, 2020. DOI:10.1101/2020.06.10.20127910.

[34] BAZAN M, MIGASIEWICZ A, MARCHWIANY M E. Task duration prediction from a textual description[J]. Procedia Computer Science, 2023, 225: 3554-3564. DOI:10.1016/j.procs.2023.10.351.

[35] ULLAH K, MUMTAZ I, AZAM ZIA M, et al. Impact of task clarity on project duration prediction in competitive crowdsourced software development[J]. IEEE Access, 2025, 13: 188251-188265. DOI:10.1109/ACCESS.2025.3621482.

[36] EBRAHIMI S, ROBINSON FAYEK A, SUMATI V. Hybrid artificial intelligence HFS-RF-PSO model for construction labor productivity prediction and optimization[J]. Algorithms, 2021, 14(7): 214. DOI:10.3390/a14070214.

### H. 疲劳与时间感知（疲劳对耗时/估计的影响）

[37] GIBOIN L S, WOLFF W. The effect of ego depletion or mental fatigue on subsequent physical endurance performance: a meta-analysis[J]. Performance Enhancement & Health, 2019, 7(1-2): 100150. DOI:10.1016/j.peh.2019.100150.

[38] DROIT-VOLET S, FAYOLLE S, GIL S. Emotion and time perception in children and adults: the effect of task difficulty[J]. Timing & Time Perception, 2016, 4(1): 7-29. DOI:10.1163/22134468-03002055.

[39] EMANUEL A, SCHENK M, HELLER A S, et al. Effects of task duration prediction errors on affective state and performance[R/OL]. PsyArXiv Preprint, 2025. DOI:10.31234/osf.io/8usp6_v1.

---

## 二、逐条源链接（按上文编号顺序）

[1] https://doi.org/10.1037/0022-3514.67.3.366
[2] https://doi.org/10.1016/S0065-2601(10)43001-4
[3] https://doi.org/10.1037/a0025996
[4] https://doi.org/10.1002/acp.893
[5] https://doi.org/10.1017/S1930297500008196
[6] https://doi.org/10.1002/1099-0992(200011/12)30:6%3C873::AID-EJSP22%3E3.0.CO;2-U
[7] https://doi.org/10.2139/ssrn.1458380
[8] https://doi.org/10.1163/22134468-bja10136
[9] https://doi.org/10.1177/009102601204100501
[10] https://doi.org/10.1145/358886.358895
[11] https://doi.org/10.1145/235833.236054
[12] https://doi.org/10.1145/1056808.1056977
[13] https://doi.org/10.1016/j.ergon.2019.06.001
[14] https://doi.org/10.1037/h0055392
[15] https://doi.org/10.4324/9780203728178-6
[16] https://doi.org/10.3758/s13423-015-0811-x （Europe PMC: https://europepmc.org/article/MED/25616778）
[17] https://doi.org/10.1037/0033-295X.100.3.363
[18] https://doi.org/10.1111/j.1553-2712.2008.00227.x （Europe PMC: https://europepmc.org/article/MED/19094141）
[19] https://doi.org/10.1016/j.paid.2007.10.022
[20] https://doi.org/10.1016/j.cognition.2014.12.004 （Europe PMC: https://europepmc.org/article/MED/25621734）
[21] https://doi.org/10.1016/j.neuroimage.2011.04.040
[22] https://doi.org/10.1145/3478431.3499359
[23] https://doi.org/10.1145/3534564
[24] https://doi.org/10.1145/3375462.3375538
[25] https://doi.org/10.19173/irrodl.v18i2.2433
[26] https://doi.org/10.19173/irrodl.v12i5.999
[27] https://doi.org/10.1109/MS.2005.73
[28] https://doi.org/10.1016/j.jss.2007.03.001
[29] https://doi.org/10.1016/j.infsof.2011.09.002
[30] https://doi.org/10.1109/TSE.2012.88
[31] https://doi.org/10.1007/s11334-017-0288-z
[32] https://doi.org/10.23919/CNSM62983.2024.10814629
[33] https://doi.org/10.1101/2020.06.10.20127910
[34] https://doi.org/10.1016/j.procs.2023.10.351
[35] https://doi.org/10.1109/ACCESS.2025.3621482
[36] https://doi.org/10.3390/a14070214
[37] https://doi.org/10.1016/j.peh.2019.100150
[38] https://doi.org/10.1163/22134468-03002055
[39] https://doi.org/10.31234/osf.io/8usp6_v1

> 复核说明：以上 DOI 已通过 Crossref `works/{DOI}` 逐条实时核验，快照见 `api/verify/`（含 `DIGEST.txt`）；摘要见 `api/selected_abstracts_04.txt` 与 `api/abstracts.json`。

---

## 三、逐篇分析

### [1] Exploring the "Planning Fallacy": Why People Underestimate Their Task Completion Times（Buehler, Griffin & Ross, 1994）

- **研究问题**：为什么人们系统性地低估自己完成任务的所需时间？是动机性愿望还是「聚焦于计划、忽略过去经验」的认知机制？
- **核心理论**：规划谬误的认知解释——人们采取「内部视角（inside view）」，聚焦于当前计划的具体步骤，而忽略过去类似任务的耗时分布（外部视角/参考类别）。
- **Independent Variables**：视角操纵（聚焦计划 vs 回顾过去经验）、任务类型、是否考虑过去完成时间。
- **Dependent Variables**：预测完成时间 vs 实际完成时间（低估幅度）。
- **主要结论**：人们倾向低估完成时间；该偏差与「聚焦计划、忽略相关过去经验」有关；引导人们考虑过去经验可减轻偏差。（Crossref 摘要不可得；结论基于题名与该文作为规划谬误认知解释奠基文献的可核验定位。）
- **结论的证据强度**：高（JPSP 经典多实验论文，被引约 711）。
- **研究局限**：实验室/学生样本；以自报估时为主；摘要不可得。
- **与本项目的关系**：直接支撑「**理论时间系统性 ≠ 实际时间**」，且低估源于忽略历史数据——这正是 Duration Predictor 应使用 `historical_duration` 而非只依赖用户自估/理论工时的理由。
- **可以支持什么系统设计**：系统估时默认以历史执行时间校准用户自估；向用户展示「过去同类任务实际耗时」。
- **可以采集什么数据**：用户自估时间、实际耗时、同类任务历史分布。
- **可以形成什么 User State**：`estimation_bias`、`duration_factor`。
- **可以作为哪一部分**：Statistical Model（actual = f(theoretical, historical)）；Rule（估时以历史为准）；LLM Harness（解释偏差）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [2] The Planning Fallacy（Buehler, Griffin & Peetz, 2010）

- **研究问题**：规划谬误的完整证据、机制、边界与修正方法是什么？
- **核心理论**：规划谬误综述；内部/外部视角、参考类别预测、自我与他人的不对称等。
- **Independent Variables**：视角、目标、反馈、任务规模等（综述）。
- **Dependent Variables**：时间/成本预测偏差（综述）。
- **主要结论**：规划谬误是稳健现象；机制涉及聚焦计划与忽视过去分布；参考类别/外部视角可减轻；不同任务与反馈条件下表现不同。（Crossref 摘要不可得；结论以该综述章节的可核验定位为准。）
- **结论的证据强度**：高（权威综述章节，被引约 66）。
- **研究局限**：综述章节；摘要不可得；部分结论来自实验室任务。
- **与本项目的关系**：为「估时偏差是可修正的系统性偏差」提供权威综合，支撑系统采用外部视角（历史分布）而非内部视角。
- **可以支持什么系统设计**：参考类别预测（reference class forecasting）式估时：用同类任务历史区间给出预估而非单点。
- **可以采集什么数据**：任务类别、类别内历史耗时分布。
- **可以形成什么 User State**：`reference_class`、`duration_factor`。
- **可以作为哪一部分**：Statistical Model（分类别估时）；Rule（估时给出区间）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [3] From Origami to Software Development: A Review of Studies on Judgment-Based Predictions of Performance Time（Halkjelsvik & Jørgensen, 2012）

- **研究问题**：跨心理学与工程/管理学的「基于判断的耗时预测」研究整体说明了什么？哪些结论稳健、哪些是假象？
- **核心理论**：耗时预测的整合综述；区分 performance time（工时）与 completion time（交付日期）两类预测。
- **Independent Variables**：任务特征（复杂度/难度）、经验、锚定、激励、任务分解、请求格式、群体估计、抽象层级、表层线索等。
- **Dependent Variables**：预测准确性/偏差方向。
- **主要结论**：**低估在工程/管理文献中更常被报告，但在心理学文献中并非如此**；挑战了「复杂性/难度与经验效应」的既有结论；质疑「小任务高估、大任务低估」的常见发现（可能是随机误差造成的统计假象）；任务分解、锚定、请求格式等均影响预测。
- **结论的证据强度**：高（Psychological Bulletin 系统综述，被引约 87）。
- **研究局限**：纳入研究异质；难以给出统一效应量；两类预测常被混淆。
- **与本项目的关系**：**本方向最关键的综述**。它直接回答「什么因素预测实际耗时/理论时间与实际时间关系」：偏差方向依赖领域，不能假设用户一定低估；任务分解会改变估时。
- **可以支持什么系统设计**：Duration Predictor 不要内置「一律乘以乐观系数」的假设；应分任务类型/领域分别校准；把「是否拆解」作为估时特征。
- **可以采集什么数据**：任务领域/类型、估时、实际耗时、是否拆解、请求格式。
- **可以形成什么 User State**：`domain_estimation_bias`、`duration_factor`。
- **可以作为哪一部分**：Statistical Model（分域偏差校准）；Rule（分域阈值）。
- **推荐优先级**：⭐⭐⭐⭐⭐（最高优先级综述）

### [4] Exploring the Time Prediction Process: Task Experience and Complexity（Thomas, Newstead & Handley, 2003）

- **研究问题**：任务经验与任务复杂度如何影响完成时间预测的准确性？
- **核心理论**：耗时预测的认知过程；任务复杂度与经验影响偏差。
- **Independent Variables**：任务经验（先做一次）、任务复杂度（3/4/5 盘汉诺塔）、任务类型（认知 vs 简单移动）。
- **Dependent Variables**：预测时间 vs 实际时间（高估/低估）。
- **主要结论**：在简单结构化的 3 盘汉诺塔上**没有低估，反而持续高估**；有先前经验者预测更准；更复杂的 4/5 盘版本偏差更小；用低认知负荷的移盘任务时出现普遍时间高估，提示**任务时长本身**可能是缺乏低估的原因。
- **结论的证据强度**：高（4 个实验，Applied Cognitive Psychology，被引约 20 但方法扎实）。
- **研究局限**：汉诺塔等实验室任务；样本有限；外推到真实工作任务需谨慎。
- **与本项目的关系**：**直接反驳「一定低估」的简单假设**，并指出经验与复杂度是估时准确性的关键调节变量——支持 Duration Predictor 使用 `task_experience` 与 `task_complexity` 特征。
- **可以支持什么系统设计**：对新任务（无经验）与高复杂任务分别调整估时偏差；记录用户是否做过同类任务。
- **可以采集什么数据**：任务复杂度标签、用户是否首次做、估时与实际。
- **可以形成什么 User State**：`task_experience`、`task_complexity`、`estimation_bias`。
- **可以作为哪一部分**：Statistical Model（偏差 = f(经验, 复杂度)）；Rule（首次任务加缓冲）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [5] More Time, More Work: How Time Limits Bias Estimates of Task Scope and Project Duration（Goswami & Urminsky, 2020）

- **研究问题**：外部给定的时间限制如何影响对任务范围与他人完成时间的估计？
- **核心理论**：时间限制→推断任务范围的过度泛化关联；任务范围感知为中介。
- **Independent Variables**：时间限制长短（是否信息性/任意、是否对方知情）。
- **Dependent Variables**：估计的完成时间、感知任务范围。
- **主要结论**：时间限制越长，估计他人完成该任务所需时间越长；即使决策者知道限制是任意且对方不知情，效应仍持续；削弱「时间限制-任务范围」关联可减弱效应；经验丰富的决策者在熟悉场景中仍受偏差影响。
- **结论的证据强度**：高（Judgment and Decision Making，被引约 3 但为受控实验）。
- **研究局限**：以估计他人耗时为主；样本为一般成人。
- **与本项目的关系**：警示系统**不要把「可用时间/截止期」当作任务规模的信号**；时间限制会污染估时，Scheduler 的截止期不应直接进入估时特征。
- **可以支持什么系统设计**：Duration Predictor 不使用 deadline/可用时长作为任务规模代理；估时基于任务内容与历史。
- **可以采集什么数据**：任务实际内容、历史耗时（而非截止期）。
- **可以形成什么 User State**：`perceived_task_scope`。
- **可以作为哪一部分**：Rule（估时特征白名单，排除 deadline）；Statistical Model。
- **推荐优先级**：⭐⭐⭐⭐

### [6] Overcoming the Planning Fallacy Through Willpower: Implementation Intentions（Koole & van't Spijker, 2000）

- **研究问题**：形成执行意图能否同时改善实际完成时间与预测准确性（缓解规划谬误）？
- **核心理论**：执行意图（if-then 计划）与规划谬误的关系。
- **Independent Variables**：是否形成执行意图。
- **Dependent Variables**：实际任务完成时间、预测完成时间（偏差）。
- **主要结论**：执行意图与更短的实际完成时间和/或更准确的预测相关。（Crossref 摘要不可得；结论以题名与该文可核验定位为准。）
- **结论的证据强度**：中高（实验论文，EJSP，被引约 40；摘要不可得）。
- **研究局限**：摘要不可得；实验室任务。
- **与本项目的关系**：连接方向3与方向4——**执行意图（何时何地如何）既改善执行，也可能改善估时**；支持把「拆解+if-then」作为估时校准手段。
- **可以支持什么系统设计**：对拆解后的任务附加执行线索，并据此校准估时。
- **可以采集什么数据**：是否有执行线索、实际耗时、估时偏差。
- **可以形成什么 User State**：`implementation_intention_use`、`duration_factor`。
- **可以作为哪一部分**：Statistical Model（线索特征入模）；LLM Harness。
- **推荐优先级**：⭐⭐⭐（摘要不可得，建议查原文）

### [7] Individuals Exhibit the Planning Fallacy for Time But Not for Money（Spiller & Lynch, 2009）

- **研究问题**：规划谬误是跨资源（时间/金钱）的一般现象，还是时间特有？「计划得越多」是否反而加剧偏差？
- **核心理论**：规划谬误的资源特异性；内部/外部视角。
- **Independent Variables**：资源类型（时间 vs 金钱）、计划倾向。
- **Dependent Variables**：预测偏差、计划行为。
- **主要结论**：3 项研究中，人们报告对金钱的规划谬误更小/更少，**对时间存在规划谬误而对金钱不存在**；该差异由资源特异性计划倾向中介；**对某资源计划越多，该资源的规划谬误越大**（「计划的讽刺效应」），与内部视角解释一致。
- **结论的证据强度**：中（工作论文，被引约 10；非同行评审，需注意）。
- **研究局限**：工作论文、未同行评审；样本与任务有限。
- **与本项目的关系**：说明时间估时偏差与金钱不同，且**过度计划可能加剧偏差**；提示系统不能简单鼓励用户「多计划」来提升估时准确度。
- **可以支持什么系统设计**：估时校准依靠历史数据而非让用户反复细化计划；避免把「计划详细度」当作准确性信号。
- **可以采集什么数据**：计划详细度、估时偏差。
- **可以形成什么 User State**：`planning_propensity`、`estimation_bias`。
- **可以作为哪一部分**：Statistical Model（计划倾向作为特征）；LLM Harness。
- **推荐优先级**：⭐⭐⭐（工作论文，需标注未同行评审）

### [8] Do People Underestimate Time? Exploring Feedback-Based Performance Time Predictions Using Brief Tasks（Halkjelsvik & Jørgensen, 2026）

- **研究问题**：在多次短任务与时长反馈的情境下，人们到底高估还是低估？「判断中心倾向」是否掩盖了低估？
- **核心理论**：判断中心倾向（central tendency of judgment）；用众数而非均值预测、忽略长尾任务等解释。
- **Independent Variables**：多次预测 + 时长反馈、任务参考框架。
- **Dependent Variables**：预测偏差（高估/低估）。
- **主要结论**：5 项研究中，研究 1/3/4 的偏差与 0 无显著差异，研究 2/5 显示**高估**，与低估假设相反；未发现过去研究中的低估被「判断中心倾向」掩盖，也未支持「用典型结果预测/忽略长尾」的解释。
- **结论的证据强度**：中高（5 个预注册式短任务研究，2026 年新文，被引 0）。
- **研究局限**：短任务、实验室；新发表引用少；任务时长范围有限。
- **与本项目的关系**：最新证据进一步表明**低估不是普适规律**；Duration Predictor 必须数据驱动、按用户/任务校准，不能内置乐观偏置。
- **可以支持什么系统设计**：以个体历史反馈为准的自校准估时；新用户先给保守区间并快速收集反馈。
- **可以采集什么数据**：每次预测与反馈、偏差随经验的变化。
- **可以形成什么 User State**：`duration_factor`（个体化倍率）。
- **可以作为哪一部分**：Statistical Model（在线校准）；Rule（新用户保守估时）。
- **推荐优先级**：⭐⭐⭐⭐（最新综述作者的前沿证据）

### [9] The Effect of Time Slack and Need for Cognition on Prediction of Task Completion（Qian & Zheng, 2012）

- **研究问题**：时间余量（time slack）与认知需求（need for cognition）如何影响任务完成时间预测的乐观程度？
- **核心理论**：时间情境操纵 + 个体差异（认知需求）调节预测乐观。
- **Independent Variables**：时间余量情境（未来/现在、宽松/紧张）、认知需求水平。
- **Dependent Variables**：预测的完成时间/乐观偏差。
- **主要结论**：人们预期未来比现在有更多时间余量，但操纵时间余量**并未减少完成时间的乐观**；**时间约束情境反而增强预测乐观**；认知需求个体差异影响时间情境操纵的效果。
- **结论的证据强度**：中（实验室实验 N=140，被引约 2）。
- **研究局限**：单实验室研究；样本有限；期刊影响较小。
- **与本项目的关系**：支持「个体差异（认知需求）调节估时偏差」，并再次警示时间约束会逆向影响估时。
- **可以支持什么系统设计**：把稳定的个体差异（如认知需求/谨慎性）作为估时特征；避免用时间压力提示来「逼」准确估时。
- **可以采集什么数据**：个体差异量表（可选）、估时与情境。
- **可以形成什么 User State**：`need_for_cognition`、`estimation_bias`。
- **可以作为哪一部分**：Statistical Model（个体差异交互项）。
- **推荐优先级**：⭐⭐⭐

### [10] The Keystroke-Level Model for User Performance Time with Interactive Systems（Card, Moran & Newell, 1980）

- **研究问题**：能否用一组基本操作符（击键、指向、心理准备等）加和预测交互任务的执行时间？
- **核心理论**：人类信息处理模型 / 击键层次模型（KLM）；任务时间 = 各基本操作符时间之和（可加性）。
- **Independent Variables**：任务的操作序列（K/P/H/M/R 等操作符及其数量）。
- **Dependent Variables**：预测执行时间 vs 实测执行时间。
- **主要结论**：KLM 能以可接受的误差预测熟练用户的交互任务执行时间，是工程上可操作的「理论时间」计算框架。（Crossref 摘要不可得；结论以该文作为 KLM 原始文献的可核验定位。）
- **结论的证据强度**：高（HCI 奠基文献，被引约 765）。
- **研究局限**：假设专家级、无错误执行；对手指/设备的参数依赖；不适合开放式认知任务。
- **与本项目的关系**：为 `theoretical_duration` 提供**可计算的工程基线**——对可枚举操作步骤的任务（表单、录入、导航），可用 KLM 估计理论下限，再乘个体倍率。
- **可以支持什么系统设计**：对操作型任务用 KLM 生成理论工时；Duration Predictor 以理论工时为特征之一。
- **可以采集什么数据**：任务操作步骤序列、实际耗时。
- **可以形成什么 User State**：`operator_speed_factor`。
- **可以作为哪一部分**：Rule（理论时间下限）；Statistical Model（理论时间→实际时间）。
- **推荐优先级**：⭐⭐⭐⭐⭐（`theoretical_duration` 的工程依据）

### [11] The GOMS Family of User Interface Analysis Techniques（John & Kieras, 1996）

- **研究问题**：KLM 之外，GOMS 家族的几种分析技术（KLM、原版 GOMS、NGOMSL、CPM-GOMS）在形式、假设与预测力上有何差异？
- **核心理论**：GOMS（Goals, Operators, Methods, Selection rules）；不同变体覆盖不同任务复杂度与并发性。
- **Independent Variables**：分析技术（4 种）。
- **Dependent Variables**：对同一任务的预测/分析结果。
- **主要结论**：四种技术可用同一任务例子对比；它们在架构假设与预测力上不同，须按任务性质选用。
- **结论的证据强度**：高（TOCHI 权威对比，被引约 395）。
- **研究局限**：面向熟练用户与交互任务；模型构建需专家。
- **与本项目的关系**：为「用哪种理论时间模型」提供选择框架——简单任务用 KLM，复杂/并发任务用 CPM-GOMS。
- **可以支持什么系统设计**：Task Generator 按任务结构选择理论时间估算方法。
- **可以采集什么数据**：任务结构复杂度、并发性。
- **可以形成什么 User State**：—（系统侧）。
- **可以作为哪一部分**：Statistical Model（理论时间特征工程）。
- **推荐优先级**：⭐⭐⭐⭐

### [12] Predicting Task Execution Time on Handheld Devices Using the Keystroke-Level Model（Luo & John, 2005）

- **研究问题**：KLM 能否预测手持设备上的任务执行时间？
- **核心理论**：KLM 在移动/手持设备的参数化。
- **Independent Variables**：手持设备任务的操作序列。
- **Dependent Variables**：预测时间 vs 实测时间。
- **主要结论**：KLM 可外推到手持设备任务。（Crossref 摘要不可得；结论以题名与该文定位为准。）
- **结论的证据强度**：中高（CHI EA，被引约 41）。
- **研究局限**：设备类型有限；摘要不可得。
- **与本项目的关系**：说明 KLM 类模型跨设备可迁移，支持系统在不同端上用统一理论时间框架。
- **可以支持什么系统设计**：多端任务理论时间估计。
- **可以采集什么数据**：设备类型、操作序列。
- **可以形成什么 User State**：`device_time_factor`。
- **可以作为哪一部分**：Statistical Model（设备特征）。
- **推荐优先级**：⭐⭐⭐（摘要不可得）

### [13] Modeling Task Completion Time of In-Vehicle Information Systems While Driving with KLM（Lee, Yoon & Ji, 2019）

- **研究问题**：如何用 KLM 建模驾驶中车载信息系统（IVIS）任务完成时间？模型与实测是否一致？
- **核心理论**：KLM + 驾驶情境的视觉/手动/心理操作符与启发式规则。
- **Independent Variables**：IVIS 任务的操作符组合。
- **Dependent Variables**：任务完成时间（预测 vs 实测）。
- **主要结论**：预测时间与观测任务完成时间呈强正相关，KLM 可用于驾驶情境的次任务完成时间预测，为界面设计提供依据。
- **结论的证据强度**：中高（用户实验 + 回归验证，被引约 26）。
- **研究局限**：特定 IVIS/驾驶情境；样本有限。
- **与本项目的关系**：提供「KLM 在真实、分心/受限情境中仍有效」的实证，增强对理论时间框架的信心。
- **可以支持什么系统设计**：对受干扰环境下的任务估时加入情境因子。
- **可以采集什么数据**：情境标签、操作序列、实际耗时。
- **可以形成什么 User State**：`context_distraction`。
- **可以作为哪一部分**：Statistical Model（情境交互项）。
- **推荐优先级**：⭐⭐⭐

### [14] The Information Capacity of the Human Motor System in Controlling the Amplitude of Movement（Fitts, 1954）

- **研究问题**：人类指向运动的时间如何由目标距离与目标宽度决定？
- **核心理论**：Fitts 定律；运动时间与「难度指数」（距离/宽度）对数成正比。
- **Independent Variables**：运动距离、目标宽度。
- **Dependent Variables**：运动时间。
- **主要结论**：运动时间随难度指数线性增加，形成著名的 Fitts 定律。（摘要不可得；结论为该定律本身的可核验内容。）
- **结论的证据强度**：高（心理物理学奠基文献，被引约 5837）。
- **研究局限**：简单指向运动；抽象认知任务不适用。
- **与本项目的关系**：为「带界面操作的任务」提供基础运动时间公式，是理论时间模型（KLM 中 P 操作符）的组成部分。
- **可以支持什么系统设计**：涉及鼠标/触摸指向的任务估时。
- **可以采集什么数据**：操作距离/目标尺寸（可自动获得）。
- **可以形成什么 User State**：`motor_speed_factor`。
- **可以作为哪一部分**：Rule/Statistical Model（理论时间组件）。
- **推荐优先级**：⭐⭐⭐（基础理论，间接应用）

### [15] Mechanisms of Skill Acquisition and the Law of Practice（Newell & Rosenbloom, 1981/2013）

- **研究问题**：技能随练习提升为何遵循「练习幂律」？其机制是什么？
- **核心理论**：练习幂律（power law of practice）；chunking 等机制解释随练习的加速与自动化。
- **Independent Variables**：练习次数。
- **Dependent Variables**：任务完成时间/绩效（随练习下降并趋稳）。
- **主要结论**：任务时间随练习次数呈幂律下降；技能获得由可积累的机制（如组块化）驱动。（摘要不可得；结论为练习幂律的可核验内容。）
- **结论的证据强度**：高（技能获得的经典章节，被引约 11 于该重印版，原始影响极大）。
- **研究局限**：摘要不可得；以实验室技能任务为主。
- **与本项目的关系**：为「**历史执行时间预测未来**」提供理论支撑——同一用户对同类任务重复执行会持续提速，`user_skill`/经验应为耗时特征。
- **可以支持什么系统设计**：Duration Predictor 引入「同类任务历史完成次数/累计练习」特征；对新用户给更保守估时。
- **可以采集什么数据**：同类任务累计次数、历次耗时序列。
- **可以形成什么 User State**：`user_skill`、`practice_count`、`learning_rate`。
- **可以作为哪一部分**：Statistical Model（耗时 = 幂律(练习次数)）；ML（序列特征）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [16] Piecewise Power Laws in Individual Learning Curves（Donner & Hardy, 2015）

- **研究问题**：个体学习曲线是平滑幂律，还是由多个幂律片段（策略切换）构成？
- **核心理论**：练习幂律的扩展——分段幂律（PPL）；局部平滑改进 + 全局策略切换。
- **Independent Variables**：练习/时间。
- **Dependent Variables**：认知任务绩效（25280 条个体学习曲线，每条 500 次测量，4 类任务）。
- **主要结论**：分段幂律显著优于单一幂律；绩效在切换点短暂下降后超过前段；**切换速率与年龄负相关**；支持「局部平滑改进 + 全局策略切换」的双过程解释。
- **结论的证据强度**：高（大规模个体曲线分析，Psychonomic Bulletin & Review，被引约 20）。
- **研究局限**：实验室认知任务；个体曲线噪声大。
- **与本项目的关系**：对「历史执行时间预测未来」的重要修正——**个体进步不是平滑的**，会有策略切换带来的阶跃；简单线性/单一幂律模型可能失效，支持引入变点/分段或 ML。
- **可以支持什么系统设计**：Duration Predictor 监控个体耗时的变点；检测到策略切换/提速后重估 `duration_factor`。
- **可以采集什么数据**：历次耗时序列（用于变点检测）。
- **可以形成什么 User State**：`learning_phase`、`duration_factor`（分段）。
- **可以作为哪一部分**：ML（变点检测/分段回归）；Statistical Model（分段幂律）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [17] The Role of Deliberate Practice in the Acquisition of Expert Performance（Ericsson, Krampe & Tesch-Römer, 1993）

- **研究问题**：专家级表现是由天赋、经验年限还是刻意练习量决定？
- **核心理论**：刻意练习（deliberate practice）理论；专家表现是长期、有针对性、有反馈的练习积累的结果。
- **Independent Variables**：刻意练习量、练习活动结构。
- **Dependent Variables**：专家表现水平。
- **主要结论**：专家表现与刻意练习量密切相关，而非单纯经验年限。（摘要不可得；结论为该理论的可核验核心主张。）
- **结论的证据强度**：高（心理学经典，被引约 6235）。
- **研究局限**：摘要不可得；回溯性练习估计；个别研究对其效应量有争议。
- **与本项目的关系**：为「经验/练习量应作为耗时与能力特征」提供理论依据，支撑 `user_skill` 的长期建模。
- **可以支持什么系统设计**：按领域维护用户练习量，用于估计耗时倍率。
- **可以采集什么数据**：领域内任务完成次数与总投入时间。
- **可以形成什么 User State**：`domain_practice_hours`、`user_skill`。
- **可以作为哪一部分**：Statistical Model（skill = f(练习量)）。
- **推荐优先级**：⭐⭐⭐⭐

### [18] Deliberate Practice and Acquisition of Expert Performance: A General Overview（Ericsson, 2008）

- **研究问题**：刻意练习的关键要素是什么？如何在医学等领域培养专家表现？
- **核心理论**：刻意练习；即时反馈、问题解决与评估时间、重复表现精炼。
- **Independent Variables**：是否采用刻意练习要素（反馈、重复、针对性）。
- **Dependent Variables**：专家表现。
- **主要结论**：观察到的表现不一定随经验年限提升；专家表现可追溯到**有针对性、有即时反馈、可重复**的刻意练习。
- **结论的证据强度**：高（权威综述，被引约 1409）。
- **研究局限**：综述；以专业领域为主。
- **与本项目的关系**：说明**经验年限≠熟练度**；系统的 `user_skill` 不应只按注册时长，而应基于有反馈的实际完成表现。
- **可以支持什么系统设计**：用实际完成质量/耗时而非加入天数估计 skill；为任务提供即时反馈以加速技能增长。
- **可以采集什么数据**：任务完成质量、反馈循环次数、耗时改善率。
- **可以形成什么 User State**：`user_skill`、`learning_rate`。
- **可以作为哪一部分**：Statistical Model；Rule（按实际表现调整难度）。
- **推荐优先级**：⭐⭐⭐⭐

### [19] Time-on-Task Mediates the Conscientiousness–Performance Relationship（Biderman 等, 2008）

- **研究问题**：尽责性（conscientiousness）对绩效的影响是否通过投入时间（time-on-task）中介？
- **核心理论**：人格→投入时间→绩效的路径模型。
- **Independent Variables**：尽责性。
- **Dependent Variables**：time-on-task、任务绩效。
- **主要结论**：time-on-task 中介尽责性与绩效的关系。（Crossref 摘要不可得；结论以题名与该文可核验定位为准。）
- **结论的证据强度**：中（PAID 论文，被引约 26；摘要不可得）。
- **研究局限**：相关设计；摘要不可得；自评人格。
- **与本项目的关系**：支持「**稳定的个体差异通过投入时间影响耗时/产出**」；用户的持续投入倾向可作为耗时预测的个体特征。
- **可以支持什么系统设计**：把用户的历史活跃度/投入时间作为耗时与完成概率特征。
- **可以采集什么数据**：每次会话时长、任务投入时间。
- **可以形成什么 User State**：`conscientiousness_proxy`（行为代理）、`time_investment`。
- **可以作为哪一部分**：Statistical Model（个体差异特征）。
- **推荐优先级**：⭐⭐⭐（摘要不可得）

### [20] Modeling Individual Differences in Response Time and Accuracy in Numeracy（Ratcliff, Thompson & McKoon, 2015）

- **研究问题**：反应时与准确性如何共同刻画个体差异？两者是否负相关？
- **核心理论**：扩散决策模型（diffusion model）；准确率关联漂移率，反应时关联速度-准确性准则，二者可分离。
- **Independent Variables**：个体（跨 4 个数值任务）。
- **Dependent Variables**：反应时、正确率、漂移率、准则设置。
- **主要结论**：准确率与反应时**并不呈现预期的负相关**——准确的人不一定快；跨任务存在稳定的「信息质量（漂移率）」与「速度-准确性准则」差异，**准则设置像是个体特质**，可被指令调节但个体间不能等同。
- **结论的证据强度**：高（Cognition，被引约 67，模型驱动多任务）。
- **研究局限**：数值/记忆任务；模型假设较强。
- **与本项目的关系**：直接支撑「**速度-准确性准则是个体稳定的速度倍率来源**」——不同用户的 `duration_factor` 部分来自其稳定的速度/准确权衡偏好，而非任务本身。
- **可以支持什么系统设计**：为用户估计稳定的速度准则（如「偏快/偏准」），用于耗时倍率；允许用户选择速度-准确性偏好。
- **可以采集什么数据**：同类任务的耗时与正确率联合分布。
- **可以形成什么 User State**：`speed_accuracy_preference`、`duration_factor`。
- **可以作为哪一部分**：Statistical Model（扩散/层级模型）；ML（个体嵌入）。
- **推荐优先级**：⭐⭐⭐⭐⭐（用户级倍率的机制依据）

### [21] Individual Differences in Cognition, Affect, and Performance: Behavioral, Neuroimaging, and Molecular Genetic Approaches（Parasuraman & Jiang, 2012）

- **研究问题**：如何用行为、神经影像与分子遗传方法研究认知、情绪与绩效的个体差异？
- **核心理论**：个体差异的多方法框架；组水平分析会掩盖亚组差异。
- **Independent Variables**：行为/神经/遗传指标。
- **Dependent Variables**：工作记忆、决策、情绪加工与真实世界绩效。
- **主要结论**：行为、fMRI、ERP 与分子遗传研究一致显示**组水平结果常掩盖重要的个体亚组差异**；多巴胺/去甲肾上腺素相关差异影响绩效。
- **结论的证据强度**：中高（NeuroImage 综述，被引约 86；部分依赖影像/遗传设备）。
- **研究局限**：综述；影像/遗传方法不可直接用于本系统，需标记。
- **与本项目的关系**：为「**耗时/表现必须个体化建模，不能用群体均值**」提供强论据；也说明个体差异来源多元（认知、情绪、遗传）。
- **可以支持什么系统设计**：Duration Predictor 必须用户级；冷启动用群体先验 + 快速个性化。
- **可以采集什么数据**：个体完成任务的行为指标（无需影像/遗传）。
- **可以形成什么 User State**：`individual_performance_profile`、`duration_factor`。
- **可以作为哪一部分**：ML（用户级模型/分层贝叶斯）。
- **推荐优先级**：⭐⭐⭐⭐

### [22] Time-on-Task Metrics for Predicting Performance（Leinonen, Castro & Hellas, 2022, SIGCSE）

- **研究问题**：粗粒度与细粒度的 time-on-task 指标，哪种更能预测学习表现？
- **核心理论**：time-on-task 作为学习投入的可观测代理；粒度影响预测力。
- **Independent Variables**：粗粒度（基于提交时间间隔）vs 细粒度（基于构造程序时的击键）。
- **Dependent Variables**：每周练习得分、考试得分、后续课程成功。
- **主要结论**：**细粒度 time-on-task 与周练习/考试成绩的相关高于粗粒度**；细粒度指标是更好的未来考试成功预测因子；建议在可用时使用尽可能细粒度的数据。
- **结论的证据强度**：高（SIGCSE 论文，被引约 14，真实课程数据）。
- **研究局限**：单门编程课程；特定日志系统。
- **与本项目的关系**：直接指导**如何观测耗时**——系统应采集尽可能细粒度的行为数据（而非仅任务开始/结束时间），以提升完成时间/表现预测。
- **可以支持什么系统设计**：任务执行中记录细粒度活动（编辑事件、保存、提交）；用细粒度 time-on-task 作为历史耗时特征。
- **可以采集什么数据**：细粒度活动日志、提交间隔、真实执行时长。
- **可以形成什么 User State**：`time_on_task`、`engagement`。
- **可以作为哪一部分**：ML/Statistical Model（time-on-task 特征）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [23] Time-on-Task Metrics for Predicting Performance（Leinonen 等, 2022, ACM Inroads）

- **研究问题**：如何用编程过程数据构造 time-on-task 指标并预测表现？（面向教学实践的版本）
- **核心理论**：time-on-task 测量。
- **Independent Variables**：time-on-task 指标定义。
- **Dependent Variables**：表现。
- **主要结论**：同 [22] 的实践版本，强调细粒度数据在可用时提升预测。（Crossref 摘要不可得；与 [22] 为同一研究的期刊版。）
- **结论的证据强度**：中高（ACM Inroads，被引约 15）。
- **研究局限**：同上；摘要不可得。
- **与本项目的关系**：作为 [22] 的补充，说明该结论在教育实践中有共识。
- **可以支持什么系统设计**：与 [22] 相同。
- **可以采集什么数据**：同上。
- **可以形成什么 User State**：`time_on_task`。
- **可以作为哪一部分**：Statistical Model。
- **推荐优先级**：⭐⭐⭐（[22] 已覆盖核心）

### [24] Rethinking Time-on-Task Estimation with Outlier Detection Accounting for Individual, Time, and Task Differences（Nguyen, 2020）

- **研究问题**：time-on-task 估计中的异常值（超长间隔）应如何处理？统一截断合理吗？
- **核心理论**：time-on-task = 连续点击间时长；异常值处理应个体化、时间化、任务化。
- **Independent Variables**：异常值处理方式（统一截断 vs 个体/时间/任务特异检测）。
- **Dependent Variables**：对学业成绩的解释方差。
- **主要结论**：统一截断（如 30/60 分钟）不合理；异常值应依**个体学习模式、学习阶段、任务性质**判定；采用个体/时间/任务特异的检测方法可多解释 **3–4%** 的成绩方差。
- **结论的证据强度**：高（LAK 论文，被引约 10，方法可复现）。
- **研究局限**：教育日志数据；单数据集。
- **与本项目的关系**：直接指导耗时数据清洗——**超长/异常耗时不能简单截断**，应结合用户、时段、任务类型判断；这直接影响 Duration Predictor 的数据质量。
- **可以支持什么系统设计**：耗时代理采用个体化异常检测；保留疑似中断的原始记录用于建模。
- **可以采集什么数据**：原始时间戳日志、任务类型、时段。
- **可以形成什么 User State**：`time_on_task`（校准后）。
- **可以作为哪一部分**：ML（异常检测）；Statistical Model。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [25] Analysis of Time-on-Task, Behavior Experiences, and Performance in Two Online Courses（Park, 2017）

- **研究问题**：不同类型真实学习任务下，time-on-task、行为互动与表现如何随学期阶段变化？
- **核心理论**：时间-on-task 与行为投入作为学习表现的相关指标。
- **Independent Variables**：课程任务类型（讨论型 vs 设计/开发型）、学期阶段。
- **Dependent Variables**：LMS 行为互动、同伴互动、time-on-task、出勤、每周任务表现。
- **主要结论**：不同任务类型的互动模式与 time-on-task 在学期不同阶段存在显著差异，说明 **time-on-task 受任务类型与阶段影响**，不能单一化解读。
- **结论的证据强度**：中高（两门课程对照，IRRODL，被引约 7）。
- **研究局限**：两门课程、样本非随机。
- **与本项目的关系**：支持把 `task_type` 与时间阶段作为耗时的分层变量；不同任务类型的耗时分布不同。
- **可以支持什么系统设计**：Duration Predictor 按任务类型分组建模；考虑学期/周期阶段效应。
- **可以采集什么数据**：任务类型、时段、行为互动、耗时。
- **可以形成什么 User State**：`task_type_profile`、`engagement_pattern`。
- **可以作为哪一部分**：Statistical Model（分层/交互）。
- **推荐优先级**：⭐⭐⭐

### [26] Quality of E-Learners' Time and Learning Performance Beyond Quantitative Time-on-Task（Romero & Barberà, 2011）

- **研究问题**：除「花了多少时间」外，时间的「质量」（可用性、弹性、时段）如何影响学习表现？
- **核心理论**：学习时间的质量维度；时间可用性、弹性、时段、星期几。
- **Independent Variables**：工作时间、time-on-task 投入、时间弹性、一天中的时段、星期几。
- **Dependent Variables**：个人与协作成绩。
- **主要结论**：时间弹性（r=.98）尤其是**在上午学习**与更好的成绩相关（个人 r=.93、协作 r=.46）；量化 time-on-task 之外的质量维度有实质影响。
- **结论的证据强度**：中高（在线硕士项目实证，IRRODL，被引约 51）。
- **研究局限**：单项目、相关设计；r 值疑似报告为拟合指标而非皮尔逊相关，解读需谨慎。
- **与本项目的关系**：支持「**何时做任务**（时段）× **能做多久**（弹性）共同影响产出」——Scheduler 的时间安排应作为耗时/表现的调节变量。
- **可以支持什么系统设计**：Scheduler 依据用户高效时段安排任务；Duration Predictor 加入时段特征。
- **可以采集什么数据**：任务执行时段、可用时间窗口、成绩/产出。
- **可以形成什么 User State**：`peak_time_windows`、`time_flexibility`。
- **可以作为哪一部分**：Rule（按时段排程）；Statistical Model（时段交互）。
- **推荐优先级**：⭐⭐⭐⭐（与项目 Scheduler 直接相关）

### [27] Practical Guidelines for Expert-Judgment-Based Software Effort Estimation（Jørgensen, 2005）

- **研究问题**：如何改进基于专家判断的软件工作量估计？
- **核心理论**：专家判断估时的偏差来源与实践准则。
- **Independent Variables**：估时流程设计（反馈、分解、检查清单等）。
- **Dependent Variables**：估时准确性。
- **主要结论**：给出改进专家判断估时的实用准则。（Crossref 摘要不可得；结论以题名与该文定位为准。）
- **结论的证据强度**：中高（IEEE Software，被引约 84）。
- **研究局限**：摘要不可得；软件行业情境。
- **与本项目的关系**：为 LLM/用户估时流程提供实践准则，支撑「让 LLM 生成估时后必须用历史数据校准」。
- **可以支持什么系统设计**：LLM Harness 估时须有检查清单与历史反馈。
- **可以采集什么数据**：估时偏差、反馈使用。
- **可以形成什么 User State**：`estimation_bias`。
- **可以作为哪一部分**：Rule（估时流程约束）；LLM Harness。
- **推荐优先级**：⭐⭐⭐（摘要不可得）

### [28] Inconsistency of Expert Judgment-Based Estimates of Software Development Effort（Grimstad & Jørgensen, 2007）

- **研究问题**：同一专家对同一任务的判断式估时是否一致？
- **核心理论**：判断式估时的可靠性（一致性）。
- **Independent Variables**：重复估计、呈现顺序等。
- **Dependent Variables**：估时一致性/离散度。
- **主要结论**：专家判断式估时存在不一致性。（Crossref 摘要不可得；结论以题名与该文定位为准。）
- **结论的证据强度**：中高（JSS，被引约 47）。
- **研究局限**：摘要不可得；软件项目情境。
- **与本项目的关系**：支持**不用纯 LLM/用户单次判断作为唯一估时来源**，而应多次采样/用历史数据稳定化。
- **可以支持什么系统设计**：对 LLM 估时做多次采样取中位数；以历史校准。
- **可以采集什么数据**：多次估时结果。
- **可以形成什么 User State**：`estimation_variance`。
- **可以作为哪一部分**：ML（集成/不确定性）；LLM Harness（多次采样）。
- **推荐优先级**：⭐⭐⭐（摘要不可得）

### [29] Systematic Literature Review of Machine Learning Based Software Development Effort Estimation Models（Wen 等, 2012）

- **研究问题**：基于机器学习的软件开发工作量估计模型的研究现状、常用算法与性能如何？
- **核心理论**：软件工作量估计的 ML 方法系统综述。
- **Independent Variables**：数据集、特征、算法。
- **Dependent Variables**：估时准确度指标。
- **主要结论**：系统梳理了 ML 工作量估计模型与数据集，指出方法学与可比性问题。（Crossref 摘要不可得；结论以题名与该综述定位为准。）
- **结论的证据强度**：高（IST 系统综述，被引约 436）。
- **研究局限**：摘要不可得；软件情境；数据集偏小、异质。
- **与本项目的关系**：回答「**简单统计模型是否足够还是需要 ML**」——ML 在群体数据上可用，但文献普遍受小样本与不可比困扰，提示本项目应先用简单可解释模型 + 个体历史，再逐步引入 ML。
- **可以支持什么系统设计**：从统计模型起步，保留升级到 ML 的接口。
- **可以采集什么数据**：任务特征、历史耗时、估时。
- **可以形成什么 User State**：`duration_factor`。
- **可以作为哪一部分**：ML（工作量估计管线设计参考）。
- **推荐优先级**：⭐⭐⭐⭐

### [30] Active Learning and Effort Estimation: Finding the Essential Content of Software Effort Estimation Data（Kocaguneli 等, 2013）

- **研究问题**：能否用主动学习从工作量估计数据中找出「最关键」的样本，以提升或维持估时性能？
- **核心理论**：主动学习/实例选择用于回归估时。
- **Independent Variables**：样本选择策略。
- **Dependent Variables**：估时准确度、所需数据量。
- **主要结论**：主动学习可识别估时数据的关键内容，减少数据需求或维持性能。（Crossref 摘要不可得；结论以题名与该文定位为准。）
- **结论的证据强度**：高（IEEE TSE，被引约 80）。
- **研究局限**：摘要不可得；软件数据集。
- **与本项目的关系**：直接指导**冷启动/小样本下的用户耗时建模**——用主动学习挑选最有信息量的历史任务来估计 `duration_factor`。
- **可以支持什么系统设计**：主动向用户询问/安排信息量最大的任务以快速个性化。
- **可以采集什么数据**：任务特征 + 耗时，用于样本选择。
- **可以形成什么 User State**：`duration_factor`（主动学习更新）。
- **可以作为哪一部分**：ML（主动学习）。
- **推荐优先级**：⭐⭐⭐⭐

### [31] Empirical Assessment of Machine Learning Models for Agile Software Development Effort Estimation Using Story Points（Satapathy & Rath, 2017）

- **研究问题**：在敏捷故事点估时中，多种 ML 模型的表现如何？
- **核心理论**：故事点作为相对估时单位 + ML 回归/分类。
- **Independent Variables**：ML 模型与项目特征。
- **Dependent Variables**：估时准确度。
- **主要结论**：对多种 ML 模型做了实证评估，给出在敏捷数据上的相对表现。（Crossref 摘要不可得；结论以题名与该文定位为准。）
- **结论的证据强度**：中高（期刊实证，被引约 49）。
- **研究局限**：摘要不可得；单一敏捷数据集族。
- **与本项目的关系**：说明「用相对单位（故事点/相对难度）× ML」可作为本项目「理论时间 + 历史」之外的替代建模范式。
- **可以支持什么系统设计**：LLM/用户先给相对难度等级，再由模型映射为耗时。
- **可以采集什么数据**：任务相对难度、耗时。
- **可以形成什么 User State**：`relative_task_difficulty`。
- **可以作为哪一部分**：ML（回归）。
- **推荐优先级**：⭐⭐⭐（摘要不可得）

### [32] Task Completion Time Prediction Scaled by Machine Learning Model Uncertainty（Kawaguchi 等, 2024）

- **研究问题**：如何在需要保守估时的资源调度场景中预测任务完成时间，并利用模型不确定性校准预测？
- **核心理论**：梯度提升决策树（GBDT）+ 模型不确定性缩放（USGBDT）。
- **Independent Variables**：任务特征、模型不确定性估计。
- **Dependent Variables**：预测完成时间是否覆盖真实值、GPU 使用效率。
- **主要结论**：先用 GBDT 预测 DL 任务完成时间，再按预期不确定性缩放；在 GPU 分时场景中**全部任务都在预测时间内完成**，GPU 使用效率从 53.4% 提升到 67.0%。
- **结论的证据强度**：中高（IEEE/IFIP CNSM 会议论文，被引约 1，含真实系统评估）。
- **研究局限**：GPU 任务场景；领域特定；引用少。
- **与本项目的关系**：提供「**预测 + 不确定性缩放**」的实用范式——Duration Predictor 可输出保守上界（避免超时）与期望值（用于排程）。
- **可以支持什么系统设计**：估时输出区间/分位数；Scheduler 用保守分位数排期、用中位数做展示。
- **可以采集什么数据**：任务特征、实际耗时、超时事件。
- **可以形成什么 User State**：`duration_uncertainty`。
- **可以作为哪一部分**：ML（分位数回归/不确定性）；Rule（保守排程）。
- **推荐优先级**：⭐⭐⭐⭐（面向调度场景，契合度高）

### [33] A Machine Learning Study to Improve Surgical Case Duration Prediction（Huang 等, 2020）

- **研究问题**：ML 能否优于医院 EMR 的历史均值基线来预测手术时长？
- **核心理论**：以历史均值（按术者或术式）为基线的监督学习（线性回归、随机森林、XGBoost）。
- **Independent Variables**：患者、操作、专科、手术团队等特征。
- **Dependent Variables**：手术时长（R²、MAE、超/低估百分比）。
- **主要结论**：XGBoost 优于其他模型：**R²=85%、MAE=30.2 分钟、在 ±10%&15min 范围内占 48%、不准确率 23.7%**；优于 EMR 历史均值基线。
- **结论的证据强度**：高（17 万余例训练 + 8,672 例外部评估，medRxiv 预印本，被引约 4；**未同行评审，需标注**）。
- **研究局限**：预印本、单医院、领域特定；时间漂移。
- **与本项目的关系**：提供「**历史均值基线 vs ML**」的直接对照证据，说明当特征丰富、样本足够时 ML 明显优于历史均值；这与本项目「先用历史倍率、再升级 ML」的路线一致。
- **可以支持什么系统设计**：Duration Predictor 基线用历史均值，数据足够后升级为 GBDT/XGBoost。
- **可以采集什么数据**：任务/用户/情境多维特征 + 实际耗时。
- **可以形成什么 User State**：`duration_factor`（模型预测）。
- **可以作为哪一部分**：ML（特征工程 + GBDT 基线/升级）。
- **推荐优先级**：⭐⭐⭐⭐⭐（最贴近的实证模板，注意预印本状态）

### [34] Task Duration Prediction from a Textual Description（Bazan 等, 2023）

- **研究问题**：能否仅从任务的文本描述预测其耗时？
- **核心理论**：文本→耗时回归（NLP 特征）。
- **Independent Variables**：任务文本描述特征。
- **Dependent Variables**：任务耗时。
- **主要结论**：从文本描述预测任务耗时是可行方向。（Crossref 摘要不可得；结论以题名与该文定位为准。）
- **结论的证据强度**：中（Procedia Computer Science，被引约 1；摘要不可得）。
- **研究局限**：摘要不可得；数据集与任务域不明。
- **与本项目的关系**：为 Task Generator/LLM Harness 直接提供「**任务描述文本可作为耗时特征**」的依据——适用于新任务冷启动（尚无历史）。
- **可以支持什么系统设计**：LLM 生成任务时同步产出估时特征；文本嵌入入模。
- **可以采集什么数据**：任务描述文本、耗时。
- **可以形成什么 User State**：—（任务侧特征）。
- **可以作为哪一部分**：ML（NLP 回归）；LLM Harness（估时提示）。
- **推荐优先级**：⭐⭐⭐（方向契合，摘要不可得）

### [35] Impact of Task Clarity on Project Duration Prediction in Competitive Crowdsourced Software Development（Ullah 等, 2025）

- **研究问题**：任务清晰度（以 BERT 语义嵌入表示）能否提升众包项目时长预测？
- **核心理论**：任务描述语义清晰度 → 时长；BERT 嵌入 + 分类/回归。
- **Independent Variables**：任务清晰度标签/语义嵌入。
- **Dependent Variables**：项目时长预测（准确率、R²）。
- **主要结论**：加入任务清晰度（BERT 嵌入）显著提升预测：**准确率 0.97、R² 0.97**，优于传统 ML 与基线（Zero Rule、Random Prediction）；强调清晰的任务描述对时长估计的重要性。
- **结论的证据强度**：中（IEEE Access，被引 0；单数据集 Topcoder，指标极高需警惕过拟合/数据泄漏）。
- **研究局限**：单一平台数据集；准确率 0.97 异常高，可能分类标签泄漏；未同行高被引。
- **与本项目的关系**：说明「**任务清晰度/描述质量**」是耗时预测的可观测特征——模糊任务应被拆解/澄清后再估时。
- **可以支持什么系统设计**：Task Generator 先提升任务描述清晰度（消除歧义）；把清晰度作为估时特征。
- **可以采集什么数据**：任务描述、清晰度标注、实际耗时。
- **可以形成什么 User State**：—（任务侧）。
- **可以作为哪一部分**：ML（文本嵌入）；Rule（低清晰度任务强制澄清）。
- **推荐优先级**：⭐⭐⭐⭐（想法有价值，但结果需谨慎复核）

### [36] Hybrid Artificial Intelligence HFS-RF-PSO Model for Construction Labor Productivity Prediction and Optimization（Ebrahimi, Robinson Fayek & Sumati, 2021）

- **研究问题**：如何用混合特征选择 + 随机森林 + 粒子群优化预测并优化建筑劳动生产率？
- **核心理论**：混合特征选择（HFS）+ ML（RF）+ 优化（PSO）。
- **Independent Variables**：影响劳动生产率的因素（经特征选择）。
- **Dependent Variables**：劳动生产率（进而可反推单位工作量耗时）。
- **主要结论**：随机森林在预测建筑劳动生产率上表现最佳；所选因素最具预测力，可降低数据复杂度；结合 PSO 进行优化。
- **结论的证据强度**：中高（Algorithms 期刊，被引约 25；领域为建筑）。
- **研究局限**：建筑劳动场景；生产率≠个人任务耗时，需转换；特征依赖领域。
- **与本项目的关系**：提供「**特征选择在耗时/生产率预测中关键**」的工程证据，支持 Duration Predictor 做特征筛选而非堆特征。
- **可以支持什么系统设计**：对耗时特征做重要性筛选；用 RF 作为可解释的基线模型。
- **可以采集什么数据**：多维任务/环境/人员特征 + 耗时。
- **可以形成什么 User State**：`productivity_factor`。
- **可以作为哪一部分**：ML（特征选择 + RF）。
- **推荐优先级**：⭐⭐⭐（跨域迁移，需转换）

### [37] The Effect of Ego Depletion or Mental Fatigue on Subsequent Physical Endurance Performance: A Meta-Analysis（Giboin & Wolff, 2019）

- **研究问题**：先前心理努力（自我损耗/心理疲劳）对后续耐力表现的影响有多大？
- **核心理论**：自我损耗/心理疲劳对后续表现的削弱；统一两条研究线。
- **Independent Variables**：先前的认知/心理努力操纵。
- **Dependent Variables**：后续身体耐力表现（元分析效应量）。
- **主要结论**：量化了自我损耗/心理疲劳对后续表现的影响。（Crossref 摘要不可得；结论以题名与该元分析定位为准。）
- **结论的证据强度**：中高（元分析，Performance Enhancement & Health，被引约 101；摘要不可得）。
- **研究局限**：摘要不可得；以身体耐力任务为因变量；对认知任务耗时的外推需谨慎。
- **与本项目的关系**：为 `fatigue` 特征提供元分析层面的依据——疲劳会削弱后续表现，可能延长耗时；但证据来自身体耐力，应用于任务耗时应标记为间接。
- **可以支持什么系统设计**：Duration Predictor 的 `fatigue` 特征只作温和调整；Scheduler 在高疲劳时避免高难度任务。
- **可以采集什么数据**：连续任务数、会话时长、任务后自评疲劳。
- **可以形成什么 User State**：`fatigue`。
- **可以作为哪一部分**：Statistical Model（疲劳项）；Rule（疲劳阈值）。
- **推荐优先级**：⭐⭐⭐（间接证据，需标记）

### [38] Emotion and Time Perception in Children and Adults: The Effect of Task Difficulty（Droit-Volet, Fayolle & Gil, 2016）

- **研究问题**：任务难度与情绪刺激如何影响时间知觉？个体认知资源起何作用？
- **核心理论**：时间知觉受注意/工作记忆资源限制；情绪刺激会改变主观时长。
- **Independent Variables**：任务难度（时间辨别比例）、情绪刺激（愤怒 vs 中性面孔）、年龄。
- **Dependent Variables**：时间二分任务的平分点与敏感性、工作记忆/注意抑制测验成绩。
- **主要结论**：在很容易的任务中，愤怒面孔使时长被判断为更长（平分点下降）；随任务难度上升，儿童表现下降且情绪效应消失；成人仍能辨别但不复现情绪效应；结论强调**可用认知资源**对时间知觉的影响。
- **结论的证据强度**：中高（实验室实验，Timing & Time Perception，被引约 24）。
- **研究局限**：时间二分实验室任务；儿童/成人样本；非真实任务耗时预测。
- **与本项目的关系**：说明**主观时间受难度与情绪影响**，与客观耗时是两回事；系统不应把用户主观感受直接当作实际耗时。
- **可以支持什么系统设计**：区分「用户感觉花了多久」与「实际耗时」两类数据；不要把主观时长作为唯一标签。
- **可以采集什么数据**：实际耗时 + 主观时长/难度自评。
- **可以形成什么 User State**：`subjective_duration_bias`。
- **可以作为哪一部分**：Statistical Model（区分主客观标签）。
- **推荐优先级**：⭐⭐⭐（理论价值，实验室设备非必需）

### [39] Effects of Task Duration Prediction Errors on Affective State and Performance（Emanuel 等, 2025）

- **研究问题**：实际任务时长比预期更长或更短，如何影响情绪与后续努力投入？
- **核心理论**：时长预测误差（PE+ / PE−）→ 情绪与努力。
- **Independent Variables**：相对预期时长（更短/更长/相等）× 5 个实验。
- **Dependent Variables**：自报情绪、任务表现、努力投入。
- **主要结论**：**比预期更短（PE+）持续改善情绪**；比预期更长（PE−）恶化情绪；PE+ 在一定程度提升表现，但效应不跨实验稳定；说明情绪与部分努力投入可仅通过**时长预期**改变。
- **结论的证据强度**：中高（5 个实验，n=628，PsyArXiv 预印本，被引 0；**未同行评审**）。
- **研究局限**：预印本、重复认知任务、实验室；表现效应不稳定。
- **与本项目的关系**：对本项目闭环至关重要——**估时误差会反作用于情绪与表现**；高估（PE+）反而提升情绪与表现，低估（PE−）破坏情绪。支持「宁可适度高估」的排程策略。
- **可以支持什么系统设计**：Duration Predictor 与 Scheduler 采用适度保守估时以避免 PE−；实时用预期管理维护情绪。
- **可以采集什么数据**：预测时长、实际时长、任务前后情绪自评、后续表现。
- **可以形成什么 User State**：`affective_state`、`prediction_error_history`。
- **可以作为哪一部分**：Rule（避免低估的排程缓冲）；Statistical Model（情绪 = f(预测误差)）。
- **推荐优先级**：⭐⭐⭐⭐⭐（直接指导闭环反馈设计，注意预印本状态）

---

## 四、对本项目重点问题的综合回答（基于上述采纳文献）

1. **什么因素预测实际耗时？**
   - **任务侧**：任务类型/领域、任务复杂度、任务清晰度/描述质量、操作步骤结构（[3][4][29][34][35]）。
   - **个体侧**：经验/练习量、技能阶段、速度-准确性偏好、尽责性等稳定个体差异（[15][16][17][18][19][20]）。
   - **情境侧**：疲劳、时段与可用时间弹性、设备/交互方式（[10][12][13][26][37]）。
   - **数据质量侧**：细粒度 time-on-task、异常值处理方式（[22][24]）。
2. **理论时间与实际时间的关系？**
   KLM/GOMS/Fitts 给出可计算的**理论下限**（熟练、无错误），实际时间 = 理论时间 × 个体/情境倍率 + 偏差（[10][11][13][14]）。偏差方向**并不总是低估**：工程/管理领域常低估，心理学领域未必（[3]）；简单短任务甚至高估（[4][8]）。因此不能内置固定的「乐观系数」。
3. **历史执行时间能预测未来吗？**
   能，且是当前最可靠的个体信号：练习幂律表明同类任务会持续提速（[15]），但个体曲线是**分段**的、存在策略切换导致的阶跃（[16]），因此应做变点/分段建模而非单一平滑外推；细粒度历史优于粗粒度（[22]）。
4. **任务难度 × 用户能力 × 任务类型如何共同影响耗时？**
   三者存在强交互：同一任务对不同 skill 用户耗时差异大（[17][18][20][21]）；复杂性改变估时偏差的方向与大小（[4]）；任务类型决定 time-on-task 分布与所需认知资源（[25][26][38]）。因此模型必须包含**任务类型 × 用户能力交互项**，并按任务类型分组建模。
5. **能否建立用户级「耗时倍率」？**
   可以，且有机制依据：稳定的速度-准确性准则（[20]）、练习/技能水平（[15][17]）、稳定个体差异（[19][21]）共同构成个体化的 `duration_factor`。实现上应以用户历史 `actual_duration / theoretical_duration` 的中位数/分位数校准，并用主动学习（[30]）快速冷启动。
6. **简单统计模型是否足够，还是需要 ML？**
   分阶段结论：
   - **冷启动/小样本**：简单可解释模型（历史均值、按任务类型与用户分组的倍率、KLM 理论时间 × 倍率）足够且更稳健（[10][29]）。
   - **数据丰富后**：ML 明显优于历史均值基线——手术时长预测 XGBoost 达 R²=85%、MAE=30.2min（[33]）；GBDT + 不确定性缩放在调度场景显著提升效率（[32]）；特征选择对性能关键（[36]）。
   - **推荐路线**：基线用统计模型（可解释、可审计，契合 RuleEngine），并行收集数据后升级为 GBDT/XGBoost，并输出**分位数/不确定性**以支持保守排程（[32]）。
7. **闭环反馈的关键设计约束**：估时误差本身会改变用户情绪与后续表现，低估（PE−）有害、适度高估（PE+）有益（[39]）。这要求 Duration Predictor 默认输出**适度保守的区间**，而非无偏点估计。

## 五、可复核性说明

- 所有采纳文献 DOI 均来自本轮 Crossref/Europe PMC 实际检索结果，并经 Crossref `works/{DOI}` 复核，快照见 `api/verify/*.json` 与 `DIGEST.txt`。
- 关键词命中与去重候选见 `api/crossref_*.json`、`api/epmc_*.json`、`api/candidates_04.txt`、`api/ranked_04.txt`；采纳文献摘要见 `api/selected_abstracts_04.txt`。
- 明确标注为**预印本/未同行评审**的条目：[7]（SSRN 工作论文）、[33]（medRxiv 预印本）、[39]（PsyArXiv 预印本）。
- 标注「Crossref 摘要不可得」的条目（[1][2][6][10][12][15][17][19][27][28][29][30][31][34][37] 等），其结论仅依据题名与该文可核验的题录/定位，未做超出证据的推断；建议获取全文后再细化效应量与变量。
