# 方向11：用户个体差异（Individual Differences）

**检索 N 篇，采纳 M 篇**：本方向实际执行检索 13 组关键词查询（PubMed E-utilities 13 组 + OpenAlex API 13 组，部分查询存在跨组重叠），原始命中条目 544 条，按 DOI/PMID/标题去重后 526 篇；经人工筛选采纳 **25 篇**（全部为 peer-reviewed 期刊论文/权威综述/元分析/经典会议论文）。

- 检索渠道：PubMed E-utilities（NCBI，`esearch`+`efetch`，含题录与摘要）、OpenAlex API（含被引量）、Crossref API（DOI 校验）、Semantic Scholar API（摘要补全）。原始数据保存在本目录 `api/` 子目录（13 个 PubMed 查询文件 + 13 个 OpenAlex 补充查询文件 + 2 个精选文献详情文件）。
- 筛选原则：优先 peer-reviewed / systematic review / meta-analysis / 高被引经典；优先变量可被系统观测（任务日志、完成时间、自评、行为数据、学习曲线）的研究；依赖神经影像/实验室设备的研究保留理论价值并明确标记。
- 本项目背景对应：User State（user_skill/duration_factor/completion_rate/time_preference/stress_response）、Duration Predictor、Statistical Model、ML（User Situation 分析）、LLM Harness。

---

## 一、采纳文献清单（GB/T 7714 引用格式）

### A. 技能习得与个体差异（为什么同一任务完成时间/概率差异大）

[1] ACKERMAN P L, CIANCIOLO A T. Cognitive, perceptual-speed, and psychomotor determinants of individual differences during skill acquisition[J]. Journal of Experimental Psychology: Applied, 2000, 6(4): 259-290. DOI:10.1037//1076-898x.6.4.259.

[2] ACKERMAN P L, KANFER R, GOFF M. Cognitive and noncognitive determinants and consequences of complex skill acquisition[J]. Journal of Experimental Psychology: Applied, 1995, 1(4): 270-304. DOI:10.1037/1076-898x.1.4.270.

[3] TAATGEN N. A model of individual differences in skill acquisition in the Kanfer–Ackerman air traffic control task[J]. Cognitive Systems Research, 2002, 3(1): 103-112. DOI:10.1016/s1389-0417(01)00049-3.

[4] CHEN S, LI Q, WANG Y, et al. Discovering individual differences in the near transfer of cognitive training by learning curve analysis of naturally occurring data[J]. Acta Psychologica, 2026, 263: 106279. DOI:10.1016/j.actpsy.2026.106279.

[5] WISNIEWSKI B, ZIERER K, HATTIE J. The power of feedback revisited: a meta-analysis of educational feedback research[J]. Frontiers in Psychology, 2020, 10: 3087. DOI:10.3389/fpsyg.2019.03087.

### B. 工作记忆与注意（认知能力维度的个体差异）

[6] JUST M A, CARPENTER P A. A capacity theory of comprehension: individual differences in working memory[J]. Psychological Review, 1992, 99(1): 122-149. DOI:10.1037/0033-295x.99.1.122.

[7] ENGLE R W. Working memory capacity as executive attention[J]. Current Directions in Psychological Science, 2002, 11(1): 19-23. DOI:10.1111/1467-8721.00160.

[8] KANE M J, ENGLE R W. The role of prefrontal cortex in working-memory capacity, executive attention, and general fluid intelligence: an individual-differences perspective[J]. Psychonomic Bulletin & Review, 2002, 9(4): 637-671. DOI:10.3758/bf03196323.

### C. 用户建模与知识追踪（可观测的建模方法）

[9] CORBETT A T, ANDERSON J R. Knowledge tracing: modeling the acquisition of procedural knowledge[J]. User Modeling and User-Adapted Interaction, 1995, 4(4): 253-278. DOI:10.1007/bf01099821.

[10] PIECH C, SPENCER J, HUANG J, et al. Deep knowledge tracing[C]//Advances in Neural Information Processing Systems. 2015: 505-513. DOI:10.48550/arxiv.1506.05908.

[11] YUDELSON M, KOEDINGER K R, GORDON G J. Individualized Bayesian knowledge tracing models[C]//Artificial Intelligence in Education. Springer, 2013: 171-180. DOI:10.1007/978-3-642-39112-5_18.

[12] ABDELRAHMAN G, WANG Q, NUNES B P. Knowledge tracing: a survey[J]. ACM Computing Surveys, 2022, 55(11): 1-37. DOI:10.1145/3569576.

[13] DESMARAIS M C, BAKER R S. A review of recent advances in learner and skill modeling in intelligent learning environments[J]. User Modeling and User-Adapted Interaction, 2011, 22(1-2): 9-38. DOI:10.1007/s11257-011-9106-8.

### D. 学业/任务绩效的心理与人格预测（元分析）

[14] RICHARDSON M, ABRAHAM C, BOND R. Psychological correlates of university students' academic performance: a systematic review and meta-analysis[J]. Psychological Bulletin, 2012, 138(2): 353-387. DOI:10.1037/a0026838.

[15] ROBBINS S B, LAUVER K, LE H, et al. Do psychosocial and study skill factors predict college outcomes? A meta-analysis[J]. Psychological Bulletin, 2004, 130(2): 261-288. DOI:10.1037/0033-2909.130.2.261.

[16] TALSMA K, SCHÜZ B, SCHWARZER R, et al. I believe, therefore I achieve (and vice versa): a meta-analytic cross-lagged panel analysis of self-efficacy and academic performance[J]. Learning and Individual Differences, 2017, 61: 136-150. DOI:10.1016/j.lindif.2017.11.015.

[17] GUL-E-ZAHRA, DANG J, CUI Y, et al. Revisiting the big five–academic performance association: a one-stage meta-analytic structural equation modeling reanalysis of 84 studies[J]. Frontiers in Psychology, 2026, 17: 1769823. DOI:10.3389/fpsyg.2026.1769823.

[18] QAZI S, SHAHAB R, SIDDIQUI I, et al. Conscientiousness and academic performance in medical students: a systematic review across training stages and assessment types[J]. Advances in Medical Education and Practice, 2026, 17: 1-14. DOI:10.2147/amep.s591397.

### E. 自我调节学习（学习策略与自我调节）

[19] SITZMANN T, ELY K. A meta-analysis of self-regulated learning in work-related training and educational attainment: what we know and where we need to go[J]. Psychological Bulletin, 2011, 137(3): 421-442. DOI:10.1037/a0022777.

[20] PANADERO E. A review of self-regulated learning: six models and four directions for research[J]. Frontiers in Psychology, 2017, 8: 422. DOI:10.3389/fpsyg.2017.00422.

[21] THEOBALD M. Self-regulated learning training programs enhance university students' academic performance, self-regulated learning strategies, and motivation: a meta-analysis[J]. Contemporary Educational Psychology, 2021, 66: 101976. DOI:10.1016/j.cedpsych.2021.101976.

### F. 自适应学习系统（个性化教学与智能辅导系统）

[22] MA W, ADESOPE O, NESBIT J C, et al. Intelligent tutoring systems and learning outcomes: a meta-analysis[J]. Journal of Educational Psychology, 2014, 106(4): 901-918. DOI:10.1037/a0037123.

[23] STEENBERGEN-HU S, COOPER H. A meta-analysis of the effectiveness of intelligent tutoring systems on college students' academic learning[J]. Journal of Educational Psychology, 2013, 106(2): 331-347. DOI:10.1037/a0034752.

[24] PENG H, MA S, SPECTOR J M. Personalized adaptive learning: an emerging pedagogical approach enabled by a smart learning environment[J]. Smart Learning Environments, 2019, 6(1). DOI:10.1186/s40561-019-0089-y.

[25] WU R, YU Z. Do AI chatbots improve students learning outcomes? Evidence from a meta-analysis[J]. British Journal of Educational Technology, 2023, 55(1): 10-33. DOI:10.1111/bjet.13334.

---

## 二、逐条源链接（按上文编号顺序）

[1] https://doi.org/10.1037//1076-898x.6.4.259 （OpenAlex: https://openalex.org/W2095069822）
[2] https://doi.org/10.1037/1076-898x.1.4.270 （OpenAlex: https://openalex.org/W2076820560）
[3] https://doi.org/10.1016/s1389-0417(01)00049-3 （OpenAlex: https://openalex.org/W2077422295）
[4] https://doi.org/10.1016/j.actpsy.2026.106279 （OpenAlex: https://openalex.org/W7125984698）
[5] https://doi.org/10.3389/fpsyg.2019.03087 （OpenAlex: https://openalex.org/W3002947507）
[6] https://doi.org/10.1037/0033-295x.99.1.122 （OpenAlex: https://openalex.org/W2072875864）
[7] https://doi.org/10.1111/1467-8721.00160 （OpenAlex: https://openalex.org/W2153432403）
[8] https://doi.org/10.3758/bf03196323 （OpenAlex: https://openalex.org/W2151179877）
[9] https://doi.org/10.1007/bf01099821 （OpenAlex: https://openalex.org/W2015040676）
[10] https://doi.org/10.48550/arxiv.1506.05908 （OpenAlex: https://openalex.org/W650350307）
[11] https://doi.org/10.1007/978-3-642-39112-5_18 （OpenAlex: https://openalex.org/W1959691478）
[12] https://doi.org/10.1145/3569576 （OpenAlex: https://openalex.org/W4307561542）
[13] https://doi.org/10.1007/s11257-011-9106-8 （OpenAlex: https://openalex.org/W1987626674）
[14] https://doi.org/10.1037/a0026838 （OpenAlex: https://openalex.org/W1968295086）
[15] https://doi.org/10.1037/0033-2909.130.2.261 （OpenAlex: https://openalex.org/W2106866721）
[16] https://doi.org/10.1016/j.lindif.2017.11.015 （OpenAlex: https://openalex.org/W2774840496）
[17] https://doi.org/10.3389/fpsyg.2026.1769823 （OpenAlex: https://openalex.org/W7134975241）
[18] https://doi.org/10.2147/amep.s591397 （OpenAlex: https://openalex.org/W7154513604）
[19] https://doi.org/10.1037/a0022777 （OpenAlex: https://openalex.org/W2139297002）
[20] https://doi.org/10.3389/fpsyg.2017.00422 （OpenAlex: https://openalex.org/W2597900308）
[21] https://doi.org/10.1016/j.cedpsych.2021.101976 （OpenAlex: https://openalex.org/W3160045617）
[22] https://doi.org/10.1037/a0037123 （OpenAlex: https://openalex.org/W2117655204）
[23] https://doi.org/10.1037/a0034752 （OpenAlex: https://openalex.org/W2316441559）
[24] https://doi.org/10.1186/s40561-019-0089-y （OpenAlex: https://openalex.org/W2922296866）
[25] https://doi.org/10.1111/bjet.13334 （OpenAlex: https://openalex.org/W4367849331）

---

## 三、逐篇分析

### [1] Cognitive, perceptual-speed, and psychomotor determinants of individual differences during skill acquisition（Ackerman & Cianciolo, 2000）

- **研究问题**：哪些能力（一般认知、知觉速度、心理运动）决定技能习得早期/中期/渐近期的个体差异？
- **核心理论**：Ackerman 技能习得个体差异理论：不同练习阶段由不同能力主导（早期=一般认知能力，后期=知觉速度/心理运动能力）。
- **Independent Variables**：能力测验（一般认知、知觉速度、心理运动）× 练习阶段（3 个实验，Kanfer-Ackerman ATC/TRACON 任务）。
- **Dependent Variables**：各练习阶段的绩效（早期/中期/渐近水平）。
- **主要结论**：早期绩效由一般认知能力预测，渐近期由知觉速度与心理运动能力预测；为"学习曲线阶段×能力"的映射提供证据。
- **结论的证据强度**：中高（JEP: Applied，被引约 219；多实验设计）。
- **研究局限**：实验室复杂任务（空中交通管制模拟）；能力测验成本高。
- **与本项目的关系**：解释"同一任务不同人完成时间差异巨大"的来源之一：不同用户处于不同习得阶段，由不同能力瓶颈主导。
- **可以支持什么系统设计**：Duration Predictor 应随用户练习次数调整权重（早期看认知能力，后期看熟练度）；新任务首次执行时间需大量不确定性。
- **可以采集什么数据**：每任务类型的完成次数（练习轨迹）、首次 vs 重复执行时长。
- **可以形成什么 User State**：`user_skill`（按技能曲线阶段）、`learning_rate`。
- **可以作为哪一部分**：Statistical Model（学习曲线阶段识别）；ML（按阶段切换预测特征）。
- **推荐优先级**：⭐⭐⭐⭐

### [2] Cognitive and noncognitive determinants and consequences of complex skill acquisition（Ackerman, Kanfer & Goff, 1995）

- **研究问题**：认知能力与非认知因素（人格、动机、自我效能）如何共同预测复杂技能习得？
- **核心理论**：整合能力-人格-动机的个体差异框架。
- **Independent Variables**：能力（空间/言语/数学/知觉速度）、人格（大五）、职业兴趣、自我评估、自我概念、动机技能、任务特定自我效能（93 名受训者、15 小时 TRACON 练习）。
- **Dependent Variables**：训练任务绩效（多次测量）、自我效能/动机思维变化。
- **主要结论**：能力测验与自我报告（自我效能、动机）对训练绩效有**独立且交互**的预测作用；自我效能随练习动态变化。
- **结论的证据强度**：中高（JEP: Applied 经典，被引约 246）。
- **研究局限**：单一任务领域（ATC 模拟）；样本 93 人。
- **与本项目的关系**：证明"完成概率"不能只看 skill，还要看自我效能与动机——二者均可观测（自评 1-2 题）。
- **可以支持什么系统设计**：将 self-efficacy 自评纳入 User State；低效能用户给予更易成功的小任务以建立信心。
- **可以采集什么数据**：任务前自评"你有多大把握完成"（1-7 分）、历史完成率。
- **可以形成什么 User State**：`self_efficacy`、`completion_rate`。
- **可以作为哪一部分**：Statistical Model（完成概率 = f(skill, self-efficacy, 动机)）；Rule（低效能→任务分块）。
- **推荐优先级**：⭐⭐⭐⭐

### [3] A model of individual differences in skill acquisition in the Kanfer–Ackerman air traffic control task（Taatgen, 2002）

- **研究问题**：能否用认知架构（ACT-R）显式建模技能习得中的个体差异？
- **核心理论**：认知建模（ACT-R 生产系统）：个体差异源于策略差异与学习参数差异，而非仅"能力值"。
- **Independent Variables**：个体参数（策略选择/学习率/能力）（建模研究）。
- **Dependent Variables**：模拟的绩效曲线 vs 真实被试绩效曲线（Kanfer-Ackerman ATC 任务）。
- **主要结论**：用基于策略与学习参数的认知模型可复现个体学习曲线差异（该文为 ACT-R 建模；具体拟合指标无开放摘要，待原文核实）。
- **结论的证据强度**：中（建模研究，Cognitive Systems Research，被引约 31；无开放摘要）。
- **研究局限**：摘要不可得；模型针对单一任务。
- **与本项目的关系**：提示个体差异可用**参数化模型**表示（策略+学习率），而非只能枚举用户画像。
- **可以支持什么系统设计**：每个用户估计"学习率参数"，用该参数预测未来同类任务的时长与成功率。
- **可以采集什么数据**：多轮同类任务的表现轨迹。
- **可以形成什么 User State**：`learning_rate`。
- **可以作为哪一部分**：Statistical Model（个体参数估计）；ML。
- **推荐优先级**：⭐⭐⭐（建模思路重要，但摘要不可得，建议获取原文）

### [4] Discovering individual differences in the near transfer of cognitive training by learning curve analysis of naturally occurring data（Chen 等, 2026）

- **研究问题**：从自然发生的（非实验室）学习数据中能否识别个体差异（迁移量、学习率）？
- **核心理论**：学习曲线分解分析；近迁移效应。
- **Independent Variables**：年龄、初始绩效水平（22,252 名 Lumosity 用户的自然数据）。
- **Dependent Variables**：任务间近迁移程度、个体学习率参数。
- **主要结论**：学习曲线分析验证了共享认知过程的任务之间存在近迁移；**年轻人迁移大于中老年人；初始绩效差的老年人反而比初始绩效好的老年人获得更大迁移**。
- **结论的证据强度**：高（超大规模生态数据 22,252 用户，Acta Psychologica；学习曲线分解方法）。
- **研究局限**：观察性；平台数据存在自选择。
- **与本项目的关系**：证明**从行为日志（完成序列+表现）估计个体学习率与迁移参数是可行的**，无需任何问卷——直接对应本项目"task logs → User State"。
- **可以支持什么系统设计**：用用户的真实任务完成轨迹估计 `learning_rate` 与技能间迁移矩阵（完成 A 类任务后对 B 类任务时长的影响）。
- **可以采集什么数据**：任务完成顺序、每任务表现（时间/正确率）、时间戳。
- **可以形成什么 User State**：`learning_rate`、`skill_transfer_matrix`、`user_skill`。
- **可以作为哪一部分**：Statistical Model（学习曲线分解）；ML；LLM Harness（向用户解释"你最近在 X 类型进步明显"）。
- **推荐优先级**：⭐⭐⭐⭐⭐（方法直接可复用于本项目数据）

### [5] The Power of Feedback Revisited: A Meta-Analysis of Educational Feedback Research（Wisniewski, Zierer & Hattie, 2020）

- **研究问题**：反馈对学生学习的影响有多大？哪些反馈形式更有效？
- **核心理论**：反馈的效果取决于信息内容（Hattie & Timperley 框架）。
- **Independent Variables**：反馈类型（内容/形式）、结果类型（435 项研究、k=994、N>61,000）。
- **Dependent Variables**：学习结果（认知/技能/动机/行为）。
- **主要结论**：反馈总体中等效果（d = 0.48）但异质性大；**反馈对认知与运动技能结果的影响大于对动机与行为结果**；不同反馈形式应视为独立处理。
- **结论的证据强度**：很高（大规模元分析，被引约 1160）。
- **研究局限**：主要面向教育场景；效果对自选任务的适用性需检验。
- **与本项目的关系**：本项目闭环的"Feedback→State Estimation"环节：反馈设计直接影响后续完成概率与时长（认知技能类任务反馈价值最高）。
- **可以支持什么系统设计**：任务后反馈内容分级（信息性反馈优先）；将反馈质量作为用户状态更新的输入。
- **可以采集什么数据**：反馈发送记录、反馈后任务表现变化。
- **可以形成什么 User State**：`feedback_response`（对反馈的敏感性）。
- **可以作为哪一部分**：LLM Harness（生成信息性反馈的指导原则）；Rule（反馈触发规则）。
- **推荐优先级**：⭐⭐⭐⭐

### [6] A capacity theory of comprehension: Individual differences in working memory（Just & Carpenter, 1992）

- **研究问题**：工作记忆容量如何约束语言理解，个体容量差异如何产生行为差异？
- **核心理论**：容量理论：加工与存储共享有限激活资源；个体激活总量不同 → 容量差异。
- **Independent Variables**：工作记忆容量（阅读广度测验）水平。
- **Dependent Variables**：句法加工模块化程度、歧义句多解释维持、理解绩效。
- **主要结论**：容量差异可解释大学生在语言理解中的质与量差异；容量大者能并行整合句法与语用信息、维持多种歧义解释。
- **结论的证据强度**：很高（Psychological Review 经典，被引约 4150）。
- **研究局限**：语言领域；容量测量（span 任务）有方法争议。
- **与本项目的关系**：工作记忆容量是"同一任务完成时间/概率差异"的基础认知来源之一；高负荷任务（多步骤、需维持中间状态）对低容量用户影响更大。
- **可以支持什么系统设计**：对低容量用户将任务拆分为更小步骤（降低同时加工要求）；时长预测加入容量因子。
- **可以采集什么数据**：任务中需要"同时保持"的元素数（任务属性）+ 用户完成绩效；可选做 span 式冷启动测验。
- **可以形成什么 User State**：`working_memory_capacity`（估计值）、`duration_factor`。
- **可以作为哪一部分**：Statistical Model（容量×任务复杂度→时长/概率）；Rule（高复杂度任务对低容量用户分块）。
- **推荐优先级**：⭐⭐⭐⭐

### [7] Working Memory Capacity as Executive Attention（Engle, 2002）

- **研究问题**：工作记忆容量（WMC）的本质是什么？它为何预测广泛认知任务？
- **核心理论**：WMC = 执行注意（executive attention）：在有干扰/冲突时维持目标导向注意的领域一般能力；WMC 与流体智力相关。
- **Independent Variables**：WMC 高/低分组。
- **Dependent Variables**：反眼跳、Stroop、双耳分听等干扰控制任务绩效。
- **主要结论**：WMC 可分离于短时记忆；是流体智力的重要成分；代表领域一般的注意控制能力，在**干扰/冲突情境**下差异最大。
- **结论的证据强度**：很高（Current Directions 权威短综述，被引约 2530）。
- **研究局限**：实验室测量；对日常任务的外推需要间接指标。
- **与本项目的关系**：高干扰环境（通知、多任务）下用户绩效差异最大——低注意控制用户在分心环境中完成时间显著更长。
- **可以支持什么系统设计**：为低注意控制用户安排专注时段/减少任务切换；任务分派避免同时进行多任务。
- **可以采集什么数据**：任务中断频率、切换后恢复时间、完成时间。
- **可以形成什么 User State**：`attention_control`（间接估计）、`stress_response`。
- **可以作为哪一部分**：Statistical Model（干扰敏感性参数）；Rule（专注时段规则）。
- **推荐优先级**：⭐⭐⭐⭐

### [8] The role of prefrontal cortex in working-memory capacity, executive attention, and general fluid intelligence（Kane & Engle, 2002）

- **研究问题**：前额叶在执行注意、WMC 与流体智力个体差异中的角色？
- **核心理论**：执行注意理论：WMC 差异源于前额叶驱动的注意控制能力差异（综述+理论整合）。
- **Independent Variables**：WMC 水平（个体差异维度，综述）。
- **Dependent Variables**：注意控制/智力任务绩效、前额叶激活（综述）。
- **主要结论**：低 WMC 者在需要抑制干扰、维持目标的任务上表现差；个体差异集中于前额叶回路。（该文为 PBR 权威综述，被引约 2250；无开放摘要，此表述为其领域公认主题。）
- **结论的证据强度**：高（权威综述，被引约 2250）。
- **研究局限**：神经影像证据为主的综述；直接工程化测量不可行。
- **与本项目的关系**：理论层确认"注意控制是跨任务稳定的个体差异维度"，支持系统为用户维护稳定的注意控制估计值。
- **可以支持什么系统设计**：User State 中维护低频率更新的能力因子（注意控制），用于解释稳定个体差异。
- **可以采集什么数据**：长期跨任务的绩效一致性、干扰情境下的表现。
- **可以形成什么 User State**：`attention_control`。
- **可以作为哪一部分**：Statistical Model（随机效应/能力因子模型）。
- **推荐优先级**：⭐⭐⭐（理论支撑，工程化间接）

### [9] Knowledge tracing: Modeling the acquisition of procedural knowledge（Corbett & Anderson, 1995）

- **研究问题**：如何从学生逐步作答数据实时追踪程序性知识掌握状态？
- **核心理论**：贝叶斯知识追踪（BKT）：每个技能有掌握/未掌握两态，观测为对/错；估计四参数（先验掌握概率、习得率、猜测率、失误率）。
- **Independent Variables**：学生的逐题作答记录（技能序列）。
- **Dependent Variables**：技能掌握概率（潜变量估计）、未来作答正确率预测。
- **主要结论**：BKT 可实时估计每个学生-技能的掌握概率并预测下次作答表现，支撑智能辅导系统的练习选择（被引约 2290 的奠基论文）。
- **结论的证据强度**：很高（奠基性论文，后续大量扩展与验证）。
- **研究局限**：假设技能独立；二值观测；参数需数据拟合。
- **与本项目的关系**：本项目 `user_skill` 的直接建模方法：用贝叶斯两态模型从每次任务成败更新技能掌握概率。
- **可以支持什么系统设计**：任务成败日志 → 每技能 mastery 概率 → 任务难度/顺序决策。
- **可以采集什么数据**：每任务的技能标签、成败（完成/放弃/质量评分）、时间戳。
- **可以形成什么 User State**：`user_skill`（每技能掌握概率）、`completion_rate`。
- **可以作为哪一部分**：Statistical Model（BKT 变体是最自然的第一实现）；ML。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [10] Deep Knowledge Tracing（Piech 等, 2015）

- **研究问题**：循环神经网络能否端到端建模学生知识状态，无需人工特征？
- **核心理论**：LSTM/RNN 从作答序列学习隐状态表示。
- **Independent Variables**：学生交互序列（题目×正确性）。
- **Dependent Variables**：下一步作答正确率（多个数据集）。
- **主要结论**：RNN 显著优于 BKT 等方法，预测更准；可解释任务结构；无需显式技能编码。
- **结论的证据强度**：高（NeurIPS，被引约 630；后续大量复现与改进）。
- **研究局限**：黑箱、需大数据、无显式不确定性；数据稀疏时不如 BKT。
- **与本项目的关系**：当用户历史数据充足时可升级 skill/完成率估计为 DKT；但本项目多为冷启动+小数据，BKT 更现实。
- **可以支持什么系统设计**：第二阶段（数据积累后）的 skill 估计升级路径。
- **可以采集什么数据**：长序列任务日志。
- **可以形成什么 User State**：`user_skill`（隐向量）、`learning_rate`。
- **可以作为哪一部分**：ML（深度模型路径）；可与 Statistical Model 形成渐进架构。
- **推荐优先级**：⭐⭐⭐⭐

### [11] Individualized Bayesian Knowledge Tracing Models（Yudelson, Koedinger & Gordon, 2013）

- **研究问题**：如何让 BKT 参数个体化（per-student）而非共享？
- **核心理论**：用多级模型/分层贝叶斯使 BKT 四参数随学生变化。
- **Independent Variables**：个体化先验/层级参数。
- **Dependent Variables**：作答预测准确率（对比标准 BKT）。
- **主要结论**：个体化 BKT 显著优于共享参数 BKT，尤其是学习率（习得概率）个体差异大。
- **结论的证据强度**：中高（AIED 会议，被引约 500）。
- **研究局限**：需要较多每用户数据；参数估计计算成本。
- **与本项目的关系**：`learning_rate` 的个体化估计方法：给每个用户单独的学习率参数（层级贝叶斯）。
- **可以支持什么系统设计**：用户冷启动用群体先验，随数据收缩/展开个体参数。
- **可以采集什么数据**：每用户逐任务成败序列。
- **可以形成什么 User State**：`learning_rate`、`user_skill`。
- **可以作为哪一部分**：Statistical Model（分层贝叶斯 BKT，与项目"Statistical-* predictor"定位契合）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [12] Knowledge Tracing: A Survey（Abdelrahman, Wang & Nunes, 2022）

- **研究问题**：知识追踪研究全貌：方法谱系、理论差异、数据集与未来方向？
- **核心理论**：KT 方法谱系：BKT（贝叶斯）→ 因子分析类（PFA）→ 深度 KT（DKT/注意力/图）等。
- **Independent Variables**：模型类型（综述维度）。
- **Dependent Variables**：预测指标（AUC 等）、数据集基准（综述）。
- **主要结论**：给出 KT 方法分类与建模差异的系统梳理、基准数据集、开放问题（稀疏性、可解释性、个体化、迁移）。
- **结论的证据强度**：高（ACM Computing Surveys 权威综述，被引约 460）。
- **研究局限**：偏教育数据科学；对"完成时间/概率"类任务型建模着墨少。
- **与本项目的关系**：为 `user_skill` 建模提供选型地图：小数据选 BKT，大数据选深度模型。
- **可以支持什么系统设计**：建模技术选型文档；评估方法（AUC/预测校准）。
- **可以采集什么数据**：任务日志（同 [9][11]）。
- **可以形成什么 User State**：`user_skill`。
- **可以作为哪一部分**：Statistical Model/ML（选型依据）；LLM Harness（向开发者解释建模选择）。
- **推荐优先级**：⭐⭐⭐⭐

### [13] A review of recent advances in learner and skill modeling in intelligent learning environments（Desmarais & Baker, 2011）

- **研究问题**：智能学习环境中学者建模（learner modeling）与技能建模的技术全景？
- **核心理论**：学生模型分类：认知诊断（DINA 等）、知识追踪、性能因子分析、约束模型、情感/元认知建模。
- **Independent Variables**：模型类型、数据来源（行为日志、作答、时序）（综述）。
- **Dependent Variables**：知识估计与预测精度（综述）。
- **主要结论**：给出学生建模方法谱系与适用条件；强调**行为日志驱动的模型**已成为主流；诊断模型与知识追踪各有适用场景。
- **结论的证据强度**：高（UMUAI 综述，被引约 450）。
- **研究局限**：2011 年视角，未覆盖深度 KT 后期发展。
- **与本项目的关系**：`user_skill`/`completion_rate` 建模的方法学总纲，帮助选择规则 vs 概率 vs 诊断模型。
- **可以支持什么系统设计**：建模方案设计决策。
- **可以采集什么数据**：行为日志、作答数据。
- **可以形成什么 User State**：`user_skill`、`completion_rate`。
- **可以作为哪一部分**：Statistical Model（建模方法选择）。
- **推荐优先级**：⭐⭐⭐⭐

### [14] Psychological correlates of university students' academic performance: A systematic review and meta-analysis（Richardson, Abraham & Bond, 2012）

- **研究问题**：大学生绩点（GPA）的心理预测因素有哪些、强度多大？
- **核心理论**：非智力因素对学业绩效的系统性预测（50 个构念、241 个数据集、1,105 个相关系数）。
- **Independent Variables**：人口学、认知能力/先验成绩、人格、动机、学习策略、社会情境因素。
- **Dependent Variables**：GPA。
- **主要结论**：高中学业成绩、SAT/ACT 等先验成绩与 GPA 中等相关；非智力因素中**绩效自我效能是最强相关（全部 50 个构念之首）**，其次为学业自我效能、成绩目标、努力调节（均中等相关）；人口学/情境因素相关很小。
- **结论的证据强度**：很高（Psychological Bulletin 元分析，被引约 3640）。
- **研究局限**：GPA 作为绩效指标；横断为主。
- **与本项目的关系**：**self-efficacy 与历史表现是完成概率最强预测因子**——支持将二者作为 User State 核心；先验成绩维度对应"技能/任务历史"。
- **可以支持什么系统设计**：`completion_rate` 预测优先使用 self-efficacy + 历史成功率；任务难度推荐参考。
- **可以采集什么数据**：自评自我效能（单题）、历史完成率。
- **可以形成什么 User State**：`self_efficacy`、`completion_rate`、`user_skill`。
- **可以作为哪一部分**：Statistical Model（完成概率模型的变量选择与先验权重）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [15] Do Psychosocial and Study Skill Factors Predict College Outcomes? A Meta-Analysis（Robbins 等, 2004）

- **研究问题**：心理社会与学习技能因素（PSF）能否在认知测验之外增量预测学业绩效与坚持？
- **核心理论**：教育坚持与动机理论（9 类 PSF 构念）。
- **Independent Variables**：成就动机、学业目标、制度承诺、社会支持、社会参与、学业自我效能、一般自我概念、学业技能、情境因素（109 项研究元分析）。
- **Dependent Variables**：GPA（绩效）与保留率（坚持）。
- **主要结论**：GPA 的最佳预测是**学业自我效能（ρ=.496）**与成就动机（ρ=.303）；保留率的最佳预测是学业技能（ρ=.366）、学业自我效能（ρ=.359）、学业目标（ρ=.340）；**PSF 对成绩与坚持有超越 SES/测验成绩/高中成绩的增量贡献**。
- **结论的证据强度**：很高（Psychological Bulletin 元分析，被引约 2480）。
- **研究局限**：大学情境；构念间相关高。
- **与本项目的关系**：区分"绩效"与"坚持"两类预测：`completion_rate` 更接近坚持（由自我效能+目标+技能预测）。
- **可以支持什么系统设计**：对易放弃用户（低自我效能/低目标）设计小步任务与目标拆解。
- **可以采集什么数据**：目标设定记录、自评自我效能。
- **可以形成什么 User State**：`self_efficacy`、`goal_commitment`。
- **可以作为哪一部分**：Statistical Model（完成率 vs 放弃概率的双模型）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [16] I believe, therefore I achieve (and vice versa): A meta-analytic cross-lagged panel analysis of self-efficacy and academic performance（Talsma 等, 2017）

- **研究问题**：自我效能与学业绩效的因果方向（双向？）？
- **核心理论**：自我效能理论（Bandura）：效能→绩效，绩效→效能（效能信念来自成功经验）。
- **Independent Variables**：自我效能、绩效（跨时点测量）。
- **Dependent Variables**：绩效、自我效能（交叉滞后路径）。
- **主要结论**：自我效能与绩效存在**双向关系**，且绩效对效能的回馈效应可能同样重要——成功经验塑造效能信念（元分析结论；无开放摘要，双向性为其核心结论）。
- **结论的证据强度**：高（元分析交叉滞后，Learning and Individual Differences，被引约 440）。
- **研究局限**：测量时点与因果推断限制。
- **与本项目的关系**：闭环反馈设计的心理依据：**安排可完成的小任务不仅是产出，还提升用户效能→提高未来完成概率**（正反馈回路）。
- **可以支持什么系统设计**：计划中保证一定比例的"高成功率任务"；任务成功后显式反馈成功。
- **可以采集什么数据**：任务成败记录、自评效能（定期）。
- **可以形成什么 User State**：`self_efficacy`（随成败更新）。
- **可以作为哪一部分**：Rule（保证成功率下限）；Statistical Model（效能-绩效联合演化模型）；LLM Harness（成功反馈文案）。
- **推荐优先级**：⭐⭐⭐⭐

### [17] Revisiting the big five–academic performance association: A one-stage meta-analytic SEM reanalysis of 84 studies（Gul-E-Zahra 等, 2026）

- **研究问题**：控制大五人格相互相关后，各人格特质对学业绩效的独特贡献？
- **核心理论**：人格-绩效；一阶段元分析结构方程（MASEM）控制特质间相关。
- **Independent Variables**：大五人格（84 项研究、N=45,477）。
- **Dependent Variables**：学业成绩。
- **主要结论**：尽责性仍最强（β=0.199）；**外向性呈显著负相关（β=−0.062）**；宜人性（0.034）与开放性（0.060）小正相关；神经质不显著。结构模型揭示了零阶相关看不到的负外向性。
- **结论的证据强度**：高（最新 MASEM，Frontiers in Psychology）。
- **研究局限**：大学样本；人格自评。
- **与本项目的关系**：人格（尤其尽责性）是**稳定**个体差异维度，可在冷启动时提供先验；外向性负向效应对"社交型用户"的含义需谨慎。
- **可以支持什么系统设计**：冷启动先验（尽责性高→更可能完成计划）；但人格测量侵入性强，建议优先用行为代理。
- **可以采集什么数据**：冷启动问卷（可选 TIPI 短量表）或行为代理（守时率、计划完成率）。
- **可以形成什么 User State**：`conscientiousness`（先验）、`completion_rate`。
- **可以作为哪一部分**：Statistical Model（先验分布参数）；LLM Harness。
- **推荐优先级**：⭐⭐⭐（人格测量侵入性 vs 增量收益需权衡）

### [18] Conscientiousness and Academic Performance in Medical Students: A Systematic Review（Qazi 等, 2026）

- **研究问题**：尽责性与医学生学业表现的关系及其随评估类型/训练阶段的变化？
- **核心理论**：尽责性-绩效关联（PRISMA 2020 系统综述，12 项研究、3,847 名学生）。
- **Independent Variables**：尽责性。
- **Dependent Variables**：学术表现（不同评估类型/训练阶段）。
- **主要结论**：尽责性与表现普遍正相关（估计范围 0.18-0.48）；在**临床评估中强于笔试**、在程序技能中弱；其预测价值在需要持续自我调节与自主努力的场景中更大；不建议用于高风险录取决策。
- **结论的证据强度**：中高（2026 系统综述）。
- **研究局限**：医学教育情境；叙述性综合（未做正式亚组元分析）。
- **与本项目的关系**：尽责性预测力在"自主、自调节型任务"（如个人任务规划执行）中最强——正是本项目的场景。
- **可以支持什么系统设计**：对低尽责性用户加强外部结构（提醒、截止、任务分解）。
- **可以采集什么数据**：提醒响应率、任务拖延模式（行为尽责性代理）。
- **可以形成什么 User State**：`conscientiousness`、`time_preference`。
- **可以作为哪一部分**：Rule（低尽责性→更高频率提醒/更小粒度任务）；Statistical Model。
- **推荐优先级**：⭐⭐⭐⭐

### [19] A meta-analysis of self-regulated learning in work-related training and educational attainment（Sitzmann & Ely, 2011）

- **研究问题**：16 个自我调节学习构念中，哪些真正预测工作培训与学业学习？
- **核心理论**：自我调节学习启发框架（目标、动机、元认知、策略等 16 构念）。
- **Independent Variables**：16 类 SRL 构念（k=430、N=90,380 元分析）。
- **Dependent Variables**：学习结果。
- **主要结论**：**目标水平、坚持、努力、自我效能是预测学习最强的 SRL 构念**，四者合计在控制认知能力与先验知识后解释学习方差 17%；计划、监控、求助、情绪控制与学习无显著关系。
- **结论的证据强度**：很高（Psychological Bulletin 元分析，被引约 900）。
- **研究局限**：工作培训/大学情境；构念测量以自评为主。
- **与本项目的关系**：`completion_rate` 的核心可观测代理：**坚持与努力**（行为：是否完成、投入时长）是最强预测——直接来自 task logs。
- **可以支持什么系统设计**：把"坚持/努力"行为化（完成率、投入时间、加班完成）作为 User State 主指标。
- **可以采集什么数据**：任务完成/放弃、实际投入时长 vs 预计时长。
- **可以形成什么 User State**：`persistence`、`effort`、`completion_rate`。
- **可以作为哪一部分**：Statistical Model（完成概率模型的核心特征集）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [20] A Review of Self-regulated Learning: Six Models and Four Directions for Research（Panadero, 2017）

- **研究问题**：六个主流 SRL 模型的异同与实证支持？SRL 研究未来方向？
- **核心理论**：SRL 模型（Zimmerman、Boekaerts、Winne & Hadwin、Pintrich、Efklides、Hadwin 等）。
- **Independent Variables**：模型维度（认知/动机/元认知/情绪）（综述）。
- **Dependent Variables**：学习与 SRL 技能（综述）。
- **主要结论**：SRL 模型构成整体性框架；**基于元分析证据，不同 SRL 模型对不同发展阶段/教育水平的学习者效果有差异**；提出四个未来方向。
- **结论的证据强度**：高（Frontiers in Psychology 综述，被引约 2800）。
- **研究局限**：模型整合视角；工程化指导少。
- **与本项目的关系**：为"反馈→状态估计→调整"闭环提供 SRL 理论框架（计划、监控、反思阶段）。
- **可以支持什么系统设计**：任务后反思问题（自我监控）；计划与复盘结构。
- **可以采集什么数据**：自评监控/反思响应。
- **可以形成什么 User State**：`self_regulation`（计划-监控-反思维度）。
- **可以作为哪一部分**：LLM Harness（反思提示词设计）；Rule（复盘触发规则）。
- **推荐优先级**：⭐⭐⭐⭐

### [21] Self-regulated learning training programs enhance university students' academic performance...: A meta-analysis（Theobald, 2021）

- **研究问题**：SRL 训练项目是否提升大学生学业表现、策略与动机？
- **核心理论**：SRL 训练干预。
- **Independent Variables**：SRL 训练项目（元分析）。
- **Dependent Variables**：学业成绩、SRL 策略使用、动机。
- **主要结论**：SRL 训练显著提升学业表现、SRL 策略与动机（元分析效应为正；具体效应量无开放摘要，待原文核实）。
- **结论的证据强度**：高（Contemporary Educational Psychology 元分析，被引约 440）。
- **研究局限**：摘要不可得；干预异质性。
- **与本项目的关系**：系统内嵌"轻量 SRL 训练"（任务前计划提示、任务后反思）可同时改善用户 skill 与完成率。
- **可以支持什么系统设计**：计划阶段的自我设问引导；复盘阶段的结构化反思。
- **可以采集什么数据**：计划质量（目标具体性）、反思完成率。
- **可以形成什么 User State**：`self_regulation`。
- **可以作为哪一部分**：LLM Harness（引导式提示）；Rule。
- **推荐优先级**：⭐⭐⭐（摘要不可得，建议获取原文）

### [22] Intelligent tutoring systems and learning outcomes: A meta-analysis（Ma 等, 2014）

- **研究问题**：ITS 相比非 ITS 教学的学习效果？效果随哪些因素变化？
- **核心理论**：ITS = 建模学习者心理状态以提供个体化指导的系统（107 个效应量、14,321 名参与者）。
- **Independent Variables**：ITS 类型、对照条件、学习结果类型、知识类型（程序/陈述性）。
- **Dependent Variables**：学习成效（效应量）。
- **主要结论**：ITS 显著优于大班教学（g=0.42）、非 ITS 计算机教学（g=0.57）、课本/练习册（g=0.35）；与个别人类辅导无显著差异（g=−0.11）；各教育层级/学科领域均正效应。
- **结论的证据强度**：很高（JEP 元分析，被引约 810）。
- **研究局限**：教育场景；效果依赖系统质量。
- **与本项目的关系**：**以学习者状态模型驱动个体化安排是有效的（元分析级证据）**——本项目"User State→调整"正是同一范式的任务规划版。
- **可以支持什么系统设计**：为"基于用户状态调整任务"提供整体正当性；计划难度自适应。
- **可以采集什么数据**：用户状态指标、任务结果。
- **可以形成什么 User State**：`user_skill`、`completion_rate`。
- **可以作为哪一部分**：Rule/Statistical Model（自适应调节的依据框架）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [23] A meta-analysis of the effectiveness of intelligent tutoring systems on college students' academic learning（Steenbergen-Hu & Cooper, 2013）

- **研究问题**：ITS 对大学生学习的效果量级与调节因素？
- **核心理论**：ITS 有效性与教师/教学法的交互。
- **Independent Variables**：ITS 类型、学科、参与方式（39 项研究、22 种 ITS）。
- **Dependent Variables**：学业学习（效应量）。
- **主要结论**：ITS 总体中等正效应（g=0.32-0.37）；**不如人类辅导但优于其他所有教学方式**；效果不因 ITS 类型/学科/参与方式显著变化；近期研究效应低于早期。
- **结论的证据强度**：很高（JEP 元分析，被引约 350）。
- **研究局限**：大学情境；"新颖性效应"担忧。
- **与本项目的关系**：对"系统提供自适应安排"的效果预期设定理性基线（中等效应，非神话）。
- **可以支持什么系统设计**：效果评估基准（对比非自适应安排）。
- **可以采集什么数据**：计划完成率/质量对比。
- **可以形成什么 User State**：`completion_rate`。
- **可以作为哪一部分**：Rule（自适应与否的对照评估设计）。
- **推荐优先级**：⭐⭐⭐⭐

### [24] Personalized adaptive learning: an emerging pedagogical approach enabled by a smart learning environment（Peng, Ma & Spector, 2019）

- **研究问题**：什么是"个性化自适应学习"？其核心要素与框架？
- **核心理论**：个性化×自适应=基于实时监测的学习者差异（个体特征、表现、发展）动态调整教学策略。
- **Independent Variables**：学习者画像、能力递进、个人学习、灵活学习环境（框架）。
- **Dependent Variables**：学习路径推荐、学习成效（概念/框架论文）。
- **主要结论**：提出个性化自适应学习四要素（个体特征、个体表现、个人发展、自适应调整）与框架；给出学习者画像模型与生成式路径推荐模式。
- **结论的证据强度**：中（框架论文，被引约 420；非实证）。
- **研究局限**：概念性框架；缺乏 RCT。
- **与本项目的关系**：**与本项目架构几乎一一对应**（learner profile=User State、adaptive adjustment=Replan/RuleEngine、learning path=Plan）；可作为系统设计的概念总纲。
- **可以支持什么系统设计**：User State 字段设计、路径推荐模式（基于画像+表现）。
- **可以采集什么数据**：画像数据、行为表现、路径选择。
- **可以形成什么 User State**：全部（user_skill/duration_factor/completion_rate/time_preference/stress_response）。
- **可以作为哪一部分**：LLM Harness（路径推荐生成框架）；Rule（画像→策略映射）。
- **推荐优先级**：⭐⭐⭐⭐

### [25] Do AI chatbots improve students learning outcomes? Evidence from a meta-analysis（Wu & Yu, 2023）

- **研究问题**：AI 聊天机器人对学习效果的影响及调节因素？
- **核心理论**：对话式 AI 辅助学习。
- **Independent Variables**：AI 聊天机器人使用（24 项随机研究元分析）、教育阶段、干预时长。
- **Dependent Variables**：学习结果。
- **主要结论**：AI 聊天机器人总体大效应；**高等教育阶段效应大于中小学**；**短期干预效应大于长期**（新颖性效应）。
- **结论的证据强度**：高（BJET 元分析，被引约 550）。
- **研究局限**：研究质量参差；新颖性效应警示。
- **与本项目的关系**：LLM Harness 的对话式反馈/解释有效（尤其成人用户），但需注意长期使用效果衰减——**反馈内容应持续变化以避免习惯化**。
- **可以支持什么系统设计**：LLM 驱动的任务说明/复盘对话；多样化表达避免疲劳。
- **可以采集什么数据**：对话使用频率、效果指标随时间变化。
- **可以形成什么 User State**：`feedback_response`。
- **可以作为哪一部分**：LLM Harness（对话式交互的设计依据与风险提示）。
- **推荐优先级**：⭐⭐⭐⭐

---

## 四、针对项目"重点问题"的文献结论汇总

1. **为什么同一任务不同人完成时间/概率差异巨大？** —— [1][2][3][6][7][14][15][19] 给出完整解释链：先验技能水平（[1][2]）、工作记忆/注意控制能力（[6][7][8]）、自我效能与动机（[14][15][16][19]）、尽责性与坚持（[17][18][19]）、学习率个体参数（[3][4]）。**结论：差异是多维稳定的，系统必须为每个用户维护独立的 skill/时长/概率状态**，任何群体均值预测都会显著失准。

2. **先验知识、技能水平、学习速度、自我效能、注意力、学习策略、历史表现、认知差异的贡献？** —— 历史表现与自我效能是元分析中绩效/坚持的最强预测（[14][15]）；先验知识与技能水平调节教学与负荷（方向5 的 [3][4]）；学习速度（习得率）是最大的个体参数差异来源（[3][11]）；注意力/工作记忆在干扰情境下差异放大（[7][8]）；学习策略/自我调节可训练且提升表现（[20][21]）。

3. **可观测的用户建模方法？** —— 行为日志驱动的概率建模是主流（[13]）：BKT 四参数模型（[9][11]）最契合小数据+可解释需求；数据充分后可升级深度模型（[10][12]）；自然行为数据（学习曲线分解）可直接估计个体学习率与迁移（[4]）；自评单题（自我效能/恢复感）提供低成本补充信号（[14][15][16]）。

4. **对项目 User State 的直接建议**：`user_skill`（每技能掌握概率，BKT 更新）；`duration_factor`（个体化时长乘子，随练习阶段与疲劳调整）；`completion_rate`（坚持/努力的直接观测，最强预测源）；`self_efficacy`（新增建议字段，自评 1 题+成败回馈）；`time_preference`（时段偏好，见 Chronotype 文献）；`stress_response`（负荷/疲劳状态，见方向5）。
