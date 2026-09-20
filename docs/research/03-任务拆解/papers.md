# 方向3：任务拆解（Task / Goal Decomposition, Subgoals, Task Granularity）

**检索 1214 篇，采纳 34 篇**：本方向实际执行关键词检索 38 组（OpenAlex API 22 组，另 2 组因免费配额中断后改用 Crossref 补检；Crossref + Europe PMC 补充 16 组，含中文关键词「任务拆解／目标拆解／目标设置／子目标」与粒度、子目标、任务分段、微任务众包、任务厌恶等定向补充）。原始命中条目去重后 **1214 条**候选，逐条按主题相关性打分、人工复核后采纳 **34 篇**。未实际检索到的经典文献一律不列入。

- 检索渠道：OpenAlex API（题录+摘要+被引量，`title_and_abstract.search`）、Crossref REST API（题录+DOI 校验）、Europe PMC REST API（含摘要）。原始数据保存在本目录 `api/`（`raw_*.json` / `*.txt` 为各组原始命中，`candidates_03.json/.txt` 为去重候选，`ranked_03.txt` 为相关性排序，`selected_abstracts_03.txt` 为采纳文献摘要，`verify/` 为 Crossref 元数据核验快照，`abstracts.json` 为摘要补检）。
- 筛选原则：优先 peer-reviewed 期刊、系统综述/元分析、高被引经典与高质量会议（CHI/CSCW/ICER/AAAI/NeurIPS 级）；优先变量可被系统观测（任务日志、完成率、子目标完成、行为数据、自评）的研究；依赖 fMRI 的神经机制研究保留理论价值并明确标记 `[fMRI]`。
- 本项目背景对应：闭环 `Plan→Execution→Feedback→State Estimation→Adjustment→New Plan`，包含 RuleEngine（硬规则）、Scheduler（排程）、Duration Predictor（目标 `actual_duration`）、Task Generator（把大目标拆成可执行任务）、LLM Harness（约束 LLM 的拆解与表达）。

---

## 一、采纳文献清单（GB/T 7714 引用格式）

### A. 目标设定、子目标与目标承诺（拆解的心理机制）

[1] LOCKE E A, LATHAM G P. Building a practically useful theory of goal setting and task motivation: a 35-year odyssey[J]. American Psychologist, 2002, 57(9): 705-717. DOI:10.1037/0003-066X.57.9.705.

[2] LOCKE E A, LATHAM G P. The development of goal setting theory: a half century retrospective[J]. Motivation Science, 2019, 5(2): 93-105. DOI:10.1037/mot0000127.

[3] KLEIN H J, WESSON M J, HOLLENBECK J R, et al. Goal commitment and the goal-setting process: conceptual clarification and empirical synthesis[J]. Journal of Applied Psychology, 1999, 84(6): 885-896. DOI:10.1037/0021-9010.84.6.885.

[4] BANDURA A, SCHUNK D H. Cultivating competence, self-efficacy, and intrinsic interest through proximal self-motivation[J]. Journal of Personality and Social Psychology, 1981, 41(3): 586-598. DOI:10.1037/0022-3514.41.3.586.

[5] LATHAM G P, SEIJTS G H. The effects of proximal and distal goals on performance on a moderately complex task[J]. Journal of Organizational Behavior, 1999, 20(4): 421-429. DOI:10.1002/(SICI)1099-1379(199907)20:4<421::AID-JOB896>3.0.CO;2-#.

[6] SEIJTS G H, LATHAM G P. The effect of distal learning, outcome, and proximal goals on a moderately complex task[J]. Journal of Organizational Behavior, 2001, 22(3): 291-307. DOI:10.1002/job.70.

[7] STOCK J, CERVONE D. Proximal goal-setting and self-regulatory processes[J]. Cognitive Therapy and Research, 1990, 14(5): 483-498. DOI:10.1007/BF01172969.

[8] BAGOZZI R P, BERGAMI M, LEONE L. Hierarchical representation of motives in goal setting[J]. Journal of Applied Psychology, 2003, 88(5): 915-943. DOI:10.1037/0021-9010.88.5.915.

### B. 执行意图与行动计划（把目标翻译成可执行步骤）

[9] GOLLWITZER P M, SHEERAN P. Implementation intentions and goal achievement: a meta-analysis of effects and processes[M]//ZANNA M P. Advances in Experimental Social Psychology: Vol 38. San Diego: Academic Press, 2006: 69-119. DOI:10.1016/S0065-2601(06)38002-1.

[10] HAGGER M S, ŁUSZCZYŃSKA A. Implementation intention and action planning interventions in health contexts: state of the research and proposals for the way forward[J]. Applied Psychology: Health and Well-Being, 2014, 6(1): 1-47. DOI:10.1111/aphw.12017.

[11] WEBB T L, SHEERAN P. Mechanisms of implementation intention effects: the role of goal intentions, self-efficacy, and accessibility of plan components[J]. British Journal of Social Psychology, 2008, 47(3): 373-395. DOI:10.1348/014466607X267010.

### C. 子目标学习与示例设计（子目标标注能否提升表现与迁移）

[12] CATRAMBONE R. The subgoal learning model: creating better examples so that students can solve novel problems[J]. Journal of Experimental Psychology: General, 1998, 127(4): 355-376. DOI:10.1037/0096-3445.127.4.355.

[13] MARGULIEUX L E, GUZDIAL M, CATRAMBONE R. Subgoal-labeled instructional material improves performance and transfer in learning to develop mobile applications[C]//Proceedings of the Ninth Annual International Conference on International Computing Education Research. New York: ACM, 2012: 71-78. DOI:10.1145/2361276.2361291.

[14] MORRISON B B, MARGULIEUX L E, GUZDIAL M. Subgoals, context, and worked examples in learning computing problem solving[C]//Proceedings of the Eleventh Annual International Conference on International Computing Education Research. New York: ACM, 2015: 21-29. DOI:10.1145/2787622.2787733.

[15] MARGULIEUX L E, MORRISON B B, DECKER A. Reducing withdrawal and failure rates in introductory programming with subgoal labeled worked examples[J]. International Journal of STEM Education, 2020, 7: 19. DOI:10.1186/s40594-020-00222-7.

[16] WEIR S, KIM J, GAJOS K Z, et al. Learnersourcing subgoal labels for how-to videos[C]//Proceedings of the 18th ACM Conference on Computer Supported Cooperative Work & Social Computing. New York: ACM, 2015: 405-416. DOI:10.1145/2675133.2675219.

[17] CHOI K, SHIN H, XIA M, et al. AlgoSolve: supporting subgoal learning in algorithmic problem-solving with learnersourced microtasks[C]//Proceedings of the 2022 CHI Conference on Human Factors in Computing Systems. New York: ACM, 2022: 1-16. DOI:10.1145/3491102.3501917.

### D. 目标梯度、进度感与任务分段（子目标如何影响投入与坚持）

[18] KIVETZ R, URMINSKY O, ZHENG Y. The goal-gradient hypothesis resurrected: purchase acceleration, illusionary goal progress, and customer retention[J]. Journal of Marketing Research, 2006, 43(1): 39-58. DOI:10.1509/jmkr.43.1.39.

[19] NUNES J C, DRÈZE X. The endowed progress effect: how artificial advancement increases effort[J]. Journal of Consumer Research, 2006, 32(4): 504-512. DOI:10.1086/500480.

[20] LOURO M J, PIETERS R, ZEELENBERG M. Dynamics of multiple-goal pursuit[J]. Journal of Personality and Social Psychology, 2007, 93(2): 174-193. DOI:10.1037/0022-3514.93.2.174.

[21] DEVEZER B, SPROTT D E, SPANGENBERG E R, et al. Consumer well-being: effects of subgoal failures and goal importance[J]. Journal of Marketing, 2014, 78(2): 118-134. DOI:10.1509/jm.11.0599.

[22] WEICK K E. Small wins: redefining the scale of social problems[J]. American Psychologist, 1984, 39(1): 40-49. DOI:10.1037/0003-066X.39.1.40.

[23] FORSYTH D K, BURT C D B. Allocating time to future tasks: the effect of task segmentation on planning fallacy bias[J]. Memory & Cognition, 2008, 36(4): 791-798. DOI:10.3758/MC.36.4.791.

### E. 层级任务分解、任务粒度与任务分析

[24] PARNAS D L. On the criteria to be used in decomposing systems into modules[J]. Communications of the ACM, 1972, 15(12): 1053-1058. DOI:10.1145/361598.361623.

[25] SEBILLOTTE S. Hierarchical planning as method for task analysis: the example of office task analysis[J]. Behaviour & Information Technology, 1988, 7(3): 275-293. DOI:10.1080/01449298808901878.

[26] BHAVNANI S K, BATES M J. Separating the knowledge layers: cognitive analysis of search knowledge through hierarchical goal decompositions[J]. Proceedings of the American Society for Information Science and Technology, 2002, 39(1): 204-213. DOI:10.1002/meet.1450390122.

[27] DIETTERICH T G. Hierarchical reinforcement learning with the MAXQ value function decomposition[J]. Journal of Artificial Intelligence Research, 2000, 13: 227-303. DOI:10.1613/jair.639.

[28] LEE Y S, SIEMSEN E. Task decomposition and newsvendor decision making[J]. Management Science, 2017, 63(10): 3226-3245. DOI:10.1287/mnsc.2016.2521.

[29] FREDERIKSEN J R, WHITE B Y. An approach to training based upon principled task decomposition[J]. Acta Psychologica, 1989, 71(1-3): 89-146. DOI:10.1016/0001-6918(89)90006-1.

[30] CHARNESS N, CAMPBELL J I D. Acquiring skill at mental calculation in adulthood: a task decomposition[J]. Journal of Experimental Psychology: General, 1988, 117(2): 115-129. DOI:10.1037/0096-3445.117.2.115.

[31] COWAN N. The magical number 4 in short-term memory: a reconsideration of mental storage capacity[J]. Behavioral and Brain Sciences, 2001, 24(1): 87-114. DOI:10.1017/S0140525X01003922.

### F. 层级规划的神经机制（依赖 fMRI，理论价值）

[32] BALAGUER J, SPIERS H, HASSABIS D, et al. Neural mechanisms of hierarchical planning in a virtual subway network[J]. Neuron, 2016, 90(4): 893-903. DOI:10.1016/j.neuron.2016.03.037. `[fMRI]`

[33] RIBAS-FERNANDES J J F, SOLWAY A, DIUK C, et al. A neural signature of hierarchical reinforcement learning[J]. Neuron, 2011, 71(2): 370-379. DOI:10.1016/j.neuron.2011.05.042. `[fMRI]`

### G. 任务厌恶与粒度设计的问题背景

[34] BLUNT A K, PYCHYL T A. Task aversiveness and procrastination: a multi-dimensional approach to task aversiveness across stages of personal projects[J]. Personality and Individual Differences, 2000, 28(1): 153-167. DOI:10.1016/S0191-8869(99)00091-4.

---

## 二、逐条源链接（按上文编号顺序）

[1] https://doi.org/10.1037/0003-066X.57.9.705 （OpenAlex: https://openalex.org/W4237356565）
[2] https://doi.org/10.1037/mot0000127 （OpenAlex: https://openalex.org/W2910015122）
[3] https://doi.org/10.1037/0021-9010.84.6.885 （OpenAlex: https://openalex.org/W1967859498）
[4] https://doi.org/10.1037/0022-3514.41.3.586 （OpenAlex: https://openalex.org/W2144190976）
[5] https://doi.org/10.1002/(SICI)1099-1379(199907)20:4%3C421::AID-JOB896%3E3.0.CO;2-%23 （OpenAlex: https://openalex.org/W1994152699）
[6] https://doi.org/10.1002/job.70 （OpenAlex: https://openalex.org/W2019557603）
[7] https://doi.org/10.1007/BF01172969 （OpenAlex: https://openalex.org/W2093466347）
[8] https://doi.org/10.1037/0021-9010.88.5.915 （OpenAlex: https://openalex.org/W1996293224）
[9] https://doi.org/10.1016/S0065-2601(06)38002-1 （OpenAlex: https://openalex.org/W1818536883）
[10] https://doi.org/10.1111/aphw.12017 （OpenAlex: https://openalex.org/W2151651278）
[11] https://doi.org/10.1348/014466607X267010 （OpenAlex: https://openalex.org/W1973708246）
[12] https://doi.org/10.1037/0096-3445.127.4.355 （OpenAlex: https://openalex.org/W2014510839）
[13] https://doi.org/10.1145/2361276.2361291 （OpenAlex: https://openalex.org/W2065907635）
[14] https://doi.org/10.1145/2787622.2787733 （OpenAlex: https://openalex.org/W2041781135）
[15] https://doi.org/10.1186/s40594-020-00222-7 （OpenAlex: https://openalex.org/W3028280248）
[16] https://doi.org/10.1145/2675133.2675219 （OpenAlex: https://openalex.org/W2206440038）
[17] https://doi.org/10.1145/3491102.3501917 （OpenAlex: https://openalex.org/W4224985605）
[18] https://doi.org/10.1509/jmkr.43.1.39
[19] https://doi.org/10.1086/500480
[20] https://doi.org/10.1037/0022-3514.93.2.174 （OpenAlex: https://openalex.org/W2010165672）
[21] https://doi.org/10.1509/jm.11.0599 （OpenAlex: https://openalex.org/W2001307472）
[22] https://doi.org/10.1037/0003-066X.39.1.40
[23] https://doi.org/10.3758/MC.36.4.791
[24] https://doi.org/10.1145/361598.361623 （OpenAlex: https://openalex.org/W2134119432）
[25] https://doi.org/10.1080/01449298808901878 （OpenAlex: https://openalex.org/W2028504295）
[26] https://doi.org/10.1002/meet.1450390122 （OpenAlex: https://openalex.org/W1977416165）
[27] https://doi.org/10.1613/jair.639 （OpenAlex: https://openalex.org/W2121517924）
[28] https://doi.org/10.1287/mnsc.2016.2521 （OpenAlex: https://openalex.org/W3126074545）
[29] https://doi.org/10.1016/0001-6918(89)90006-1 （OpenAlex: https://openalex.org/W2042970868）
[30] https://doi.org/10.1037/0096-3445.117.2.115 （OpenAlex: https://openalex.org/W2062740422）
[31] https://doi.org/10.1017/S0140525X01003922 （OpenAlex: https://openalex.org/W2166667242）
[32] https://doi.org/10.1016/j.neuron.2016.03.037 （OpenAlex: https://openalex.org/W2400568150）
[33] https://doi.org/10.1016/j.neuron.2011.05.042
[34] https://doi.org/10.1016/S0191-8869(99)00091-4

> 复核说明：以上元数据已通过 Crossref `works/{DOI}` 逐条核验，快照见 `api/verify/`，摘要见 `api/selected_abstracts_03.txt`。

---

## 三、逐篇分析

### [1] Building a Practically Useful Theory of Goal Setting and Task Motivation: A 35-Year Odyssey（Locke & Latham, 2002）

- **研究问题**：如何把 35 年目标设定研究整合成可实践的理论，目标为何、何时、如何影响任务动机与绩效？
- **核心理论**：目标设定理论（Goal-Setting Theory）。核心命题：具体且有难度的目标优于模糊的「尽力而为」目标；目标通过四种机制起作用——引导注意、调动努力、增强坚持、促进策略搜索；目标承诺、反馈、自我效能、任务复杂度为调节变量。
- **Independent Variables**：目标具体性、目标难度、目标来源（分配 vs 参与设定）、反馈、任务复杂度。
- **Dependent Variables**：任务绩效、动机、目标承诺、策略使用。
- **主要结论**：具体有难度的目标在人们具备能力并接受目标时提升绩效；模糊目标效果弱；目标通过策略与努力中介发挥作用；作者在文中明确讨论了理论的边界与局限。（原始摘要未开放，结论依据题名与文中原理性陈述；建议核对原文。）
- **结论的证据强度**：高（数十年的归纳性证据整合，被引约 6000）。
- **研究局限**：以工作/实验室任务为主；对「目标应拆到多细」未给出量化阈值；强目标在复杂学习任务上可能适得其反（见 [6]）。
- **与本项目的关系**：为「系统如何给定目标」提供第一性原理——目标是可执行拆解的锚点，拆解应服务于「具体、可反馈、可承诺」。
- **可以支持什么系统设计**：Task Generator 在拆解后为每个子任务生成「具体可验证的完成标准」；RuleEngine 要求每个任务有明确的完成判据。
- **可以采集什么数据**：任务目标文本、完成判据、自报目标难度/承诺。
- **可以形成什么 User State**：`goal_commitment`、`goal_specificity_preference`。
- **可以作为哪一部分**：LLM Harness（约束拆解输出结构化目标）；Rule（任务必须有 completion criteria）。
- **推荐优先级**：⭐⭐⭐⭐⭐（理论基石）

### [2] The Development of Goal Setting Theory: A Half-Century Retrospective（Locke & Latham, 2019）

- **研究问题**：目标设定理论 50 年演进中，哪些结论具有跨情境的一般性？哪些新发现改变了应用方式？
- **核心理论**：目标设定理论；强调理论由归纳（数百项研究、数千被试）而非演绎形成，识别了中介与调节变量。
- **Independent Variables**：参与者、任务、国别、目标来源、场景、实验设计、结果变量、分析层级、时间跨度（一般性检验维度）。
- **Dependent Variables**：绩效及其跨层级结果。
- **主要结论**：目标效应在人群、任务、文化、层级与时间跨度上具有一般性；**学习目标与绩效目标的选择**（当任务需要先获得知识时用学习目标）、阈下启动目标、以及「写下目标」会增强目标效应。
- **结论的证据强度**：高（权威回顾，被引约 650）。
- **研究局限**：仍以个体/组织实验为主，未直接给出任务粒度算法。
- **与本项目的关系**：为「新手遇到需要先学习的任务时应给学习型目标而非产出型目标」提供依据，直接影响拆解策略与任务措辞。
- **可以支持什么系统设计**：当 `user_skill` 低或任务新时，将任务目标形式设为「学习/掌握 X」而非「产出 X」。
- **可以采集什么数据**：任务类型（学习/产出）、用户先验熟练度、目标措辞。
- **可以形成什么 User State**：`user_skill`、`goal_type_preference`。
- **可以作为哪一部分**：Rule（低 skill 场景改判为学习目标）；LLM Harness（生成学习型目标措辞）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [3] Goal Commitment and the Goal-Setting Process（Klein 等, 1999）

- **研究问题**：目标承诺在目标设定→绩效链路中扮演什么角色？其前因与后果是什么？
- **核心理论**：目标设定理论中的目标承诺构念。
- **Independent Variables**：目标承诺的前因（吸引力、期望、参与等，元分析汇总）。
- **Dependent Variables**：目标承诺、任务绩效。
- **主要结论**：基于 83 个独立样本的元分析澄清了目标承诺的构念地位与前因后果，确认目标承诺是「目标→绩效」关系的关键环节。（摘要仅给出总体结论，具体效应量需查原文表。）
- **结论的证据强度**：高（元分析，83 个独立样本，被引约 557）。
- **研究局限**：以组织情境为主；承诺的实时测量依赖自评。
- **与本项目的关系**：说明「拆出来的子任务若不能被用户接受/承诺，则不会转化为执行」；任务拆解需考虑承诺而非只考虑逻辑完备。
- **可以支持什么系统设计**：可让用户对 AI 拆解结果进行确认/编辑（提高承诺）；对承诺低的任务补充理由或降低难度。
- **可以采集什么数据**：用户对拆解的接受/编辑行为、是否跳过任务、任务后自报承诺。
- **可以形成什么 User State**：`goal_commitment`。
- **可以作为哪一部分**：Rule（低承诺任务触发再协商/重新拆解）；LLM Harness（生成提升承诺的说明）。
- **推荐优先级**：⭐⭐⭐⭐

### [4] Cultivating Competence, Self-Efficacy, and Intrinsic Interest Through Proximal Self-Motivation（Bandura & Schunk, 1981）

- **研究问题**：近距离（proximal）子目标 vs 远距离目标 vs 无目标，对自我指导学习、自我效能与内在兴趣有何影响？
- **核心理论**：社会认知理论；子目标通过提供即时可得的掌握体验来培养自我效能。
- **Independent Variables**：目标条件（se proximal 子目标 / 远距离目标 / 无目标）。
- **Dependent Variables**：自导学习进度、数学操作掌握度、自我效能判断、内在兴趣、自我效能-成绩一致性。
- **主要结论**：近距离子目标组的儿童进步最快、掌握度最高，并形成更强的自我效能与内在兴趣；**远距离目标组几乎没有可观察效果**；子目标提升了对自身能力的准确判断。
- **结论的证据强度**：高（经典实验，被引约 2560）。
- **研究局限**：样本为数学落后儿童；任务为结构化算术。
- **与本项目的关系**：直接支撑「**子目标能提高完成率/坚持**」，尤其是把大目标切到「近期可完成」时；提示拆解深度应使子任务到达「近期可完成」尺度。
- **可以支持什么系统设计**：Task Generator 优先把任务拆到可在一次学习/工作时段内完成；Scheduler 让近期子目标密集出现。
- **可以采集什么数据**：子任务完成时间、完成率、自报自信、下一任务启动延迟。
- **可以形成什么 User State**：`self_efficacy`、`subgoal_completion_rate`。
- **可以作为哪一部分**：Rule（任务粒度上限：单次可完成）；Statistical Model（完成率 = f(子目标距离)）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [5] The Effects of Proximal and Distal Goals on Performance on a Moderately Complex Task（Latham & Seijts, 1999）

- **研究问题**：在中等复杂任务上，「近端子目标 + 远端目标」是否优于只给远端目标或「尽力而为」？
- **核心理论**：目标设定理论 + 子目标的自我效能/反馈机制。
- **Independent Variables**：目标条件（proximal+distal / 仅 distal / do-your-best）。
- **Dependent Variables**：产出（计件收入）、自我效能。
- **主要结论**：仅给远距离目标组的收入**低于**「尽力而为」组；但「近端子目标 + 远距离目标」组收入显著高于「尽力而为」组；自我效能只在「近端+远端」组显著上升。作者提出子目标的作用更多是**信息性**（聚焦合适策略）而非仅通过目标承诺的动机性。
- **结论的证据强度**：高（受控实验，N=39，被引约 204）。
- **研究局限**：样本小、任务为简单手工计件；外部效度有限。
- **与本项目的关系**：关键警示——**只给远端大目标可能还不如不给具体目标**；必须有近端子目标。直接支持系统的「拆解到近期可完成单元」。
- **可以支持什么系统设计**：Scheduler 始终把远端目标映射到近端子目标；禁止向用户只展示一个巨大的最终目标。
- **可以采集什么数据**：子目标完成事件、完成间隔、自报自我效能。
- **可以形成什么 User State**：`self_efficacy`、`subgoal_density_preference`。
- **可以作为哪一部分**：Rule（远端目标必须配近端子目标）；Statistical Model（绩效 = f(目标距离)）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [6] The Effect of Distal Learning, Outcome, and Proximal Goals on a Moderately Complex Task（Seijts & Latham, 2001）

- **研究问题**：当任务需要先获取知识时，远端「学习目标」vs「产出目标」，以及是否附加近端目标，如何影响绩效？
- **核心理论**：目标设定理论中的学习目标/产出目标区分；策略发现为中介。
- **Independent Variables**：远端目标类型（学习/产出）× 是否配近端目标 × do-your-best。
- **Dependent Variables**：排课任务绩效、目标承诺、发现的策略数、自我效能。
- **主要结论**：在需要学习的任务上，**具体困难的学习目标优于「尽力而为」**，而具体困难的产出目标反而不如「尽力而为」；学习目标组承诺更高；「远端学习目标 + 近端目标」组发现的策略最多；但给产出/学习远端目标再加近端**产出**目标并未提升绩效。
- **结论的证据强度**：高（受控实验，N=96，被引约 190）。
- **研究局限**：实验室排课任务；结论对任务类型的边界仍需拓展。
- **与本项目的关系**：支撑「**不同任务类型粒度/目标类型不同**」——需先学习的任务应拆成学习子目标，而非直接切产出里程碑。
- **可以支持什么系统设计**：Task Generator 先判断任务是否需要学习，再决定子目标形式；对学习型任务用「掌握 X」子目标。
- **可以采集什么数据**：任务所需的先验知识、策略使用迹象（改错、重试）、学习子目标完成。
- **可以形成什么 User State**：`learning_goal_ratio`、`user_skill`。
- **可以作为哪一部分**：Rule（按任务类型选择目标形式）；LLM Harness（生成学习型子目标）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [7] Proximal Goal-Setting and Self-Regulatory Processes（Stock & Cervone, 1990）

- **研究问题**：近端子目标如何影响自我调节过程（努力、坚持、自我反应）？
- **核心理论**：自我调节的社会认知模型；子目标作为自我评估与调节的参照。
- **Independent Variables**：目标接近度（近端/远端）。
- **Dependent Variables**：自我调节指标（努力、坚持、自我反应）。
- **主要结论**：近端子目标促进更有效的自我调节。（原始摘要未开放，Crossref 核验元数据；结论以题名与该文在目标设定文献中的定位为准，建议核对原文。）
- **结论的证据强度**：中高（经典实验，被引约 136；摘要不可得）。
- **研究局限**：年代较早、样本与任务有限；摘要不可得。
- **与本项目的关系**：为「子目标→自我调节→坚持」补一条机制证据，支撑拆解提升完成率。
- **可以支持什么系统设计**：在子任务完成后立即给出进度反馈以触发自我调节。
- **可以采集什么数据**：子任务完成后的继续/停止行为、自评努力。
- **可以形成什么 User State**：`self_regulation`、`subgoal_completion_rate`。
- **可以作为哪一部分**：Rule（子目标完成后立即给反馈）；Statistical Model。
- **推荐优先级**：⭐⭐⭐（摘要不可得，需查原文）

### [8] Hierarchical Representation of Motives in Goal Setting（Bagozzi 等, 2003）

- **研究问题**：人们选择目标背后的「理由」是否构成可揭示的层级动机网络？
- **核心理论**：目标设定的动机层级表征；用「目标理由」抽取情境特异动机及其连接。
- **Independent Variables**：动机/理由及其层级连接。
- **Dependent Variables**：态度、再入伍意向、对军队的承诺。
- **主要结论**：理由可被组织为相互连接的层级动机网络，并显著预测态度、意向与承诺。
- **结论的证据强度**：中高（多组军队样本，N≈586，被引约 142）。
- **研究局限**：军队志愿场景特殊；层级由事后访谈/问卷构建。
- **与本项目的关系**：说明**目标之上还有动机层**；系统拆解目标时应尽量连接到用户认可的更高层动机，否则子任务难以承诺。
- **可以支持什么系统设计**：让用户在拆解时标注/确认「为什么做这个」，用于排序与提醒文案。
- **可以采集什么数据**：用户目标理由文本、动机标签、承诺评分。
- **可以形成什么 User State**：`goal_motivation_hierarchy`、`why_statement`。
- **可以作为哪一部分**：LLM Harness（抽取动机层级）；Rule（缺动机的任务降低优先级）。
- **推荐优先级**：⭐⭐⭐⭐

### [9] Implementation Intentions and Goal Achievement: A Meta-Analysis（Gollwitzer & Sheeran, 2006）

- **研究问题**：在目标意图之外形成「如果-那么」执行意图，能否提升目标达成？机制为何？
- **核心理论**：执行意图/行动计划理论；执行意图把行为控制权交给情境线索（自动化启动）。
- **Independent Variables**：是否形成执行意图（含 when/where/how）。
- **Dependent Variables**：目标达成率；启动、屏蔽干扰、脱离失败路径、保存后续能力四类子结果。
- **主要结论**：94 项独立检验汇总，执行意图对目标达成有**中等偏大**正向效应（d = 0.65）；支持机会线索可得性提升与线索-反应联结自动化的机制。
- **结论的证据强度**：高（元分析，94 项检验，被引约 3262）。
- **研究局限**：多为短期行为目标；对复杂认知任务的直接证据较少。
- **与本项目的关系**：这是「**把任务拆到可执行**」的最强证据之一：有效的拆解不只是分解内容，还要指定**何时、何地、如何**（若 X 情形，则做 Y）。
- **可以支持什么系统设计**：Task Generator 为每个任务生成 if-then 执行线索（时间/地点/触发条件）；Scheduler 把线索绑定到具体时段。
- **可以采集什么数据**：用户设定的触发情境、任务是否在其后启动、启动延迟。
- **可以形成什么 User State**：`implementation_intention_use`、`cue_responsiveness`。
- **可以作为哪一部分**：Rule（任务必须含 when/where 线索）；LLM Harness（生成 if-then 文案）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [10] Implementation Intention and Action Planning Interventions in Health Contexts（Hagger & Łuszczyńska, 2014）

- **研究问题**：执行意图与行动计划干预的现状如何？怎样设计才最有效？
- **核心理论**：执行意图/行动计划；综述其定义、格式、机制与设计。
- **Independent Variables**：干预设计要素（if-then 格式、线索显著性、是否给示例、是否引导、是否有 booster）。
- **Dependent Variables**：健康行为改变。
- **主要结论**：计划干预总体有效且成本低；但效应异质性大、少有无偏随机试验与客观行为测量。最优设计应：采用 if-then 计划、考虑显著相关线索、给出线索示例、**由引导而非用户自定义**、并包含 booster。
- **结论的证据强度**：中高（权威综述/专家共识，被引约 600）。
- **研究局限**：以健康行为为主；研究质量参差。
- **与本项目的关系**：指导系统如何生成执行线索——**由系统引导生成**（而非完全让用户自己想），并提供线索示例与复提醒。
- **可以支持什么系统设计**：拆解向导由 LLM 提供候选触发情境；提供「重复/booster」提醒机制。
- **可以采集什么数据**：线索采纳率、提醒后的启动率、复提醒效果。
- **可以形成什么 User State**：`cue_responsiveness`、`planning_support_need`。
- **可以作为哪一部分**：Rule（新用户默认引导式 if-then）；LLM Harness（生成候选线索示例）。
- **推荐优先级**：⭐⭐⭐⭐

### [11] Mechanisms of Implementation Intention Effects（Webb & Sheeran, 2008）

- **研究问题**：执行意图的效应是来自更多深思（goal intentions/self-efficacy），还是来自计划成分的可得性与线索-反应联结？
- **核心理论**：执行意图机制争论。
- **Independent Variables**：执行意图形成；计划成分可得性；线索-反应联结强度。
- **Dependent Variables**：目标意图、自我效能、目标达成。
- **主要结论**：66 项检验的元分析显示执行意图对目标意图与自我效能几乎无影响；效应由**指定情境线索的可得性**与**线索-反应联结强度**共同中介。即执行意图不是「更想」，而是「更自动化地被触发」。
- **结论的证据强度**：高（元分析 + 实验，被引约 350）。
- **研究局限**：机制测量依赖反应时/可及性任务。
- **与本项目的关系**：说明系统生成的执行线索可通过**提高线索可及性**直接提升启动率——对「降低启动阻力、减少拖延」尤其关键。
- **可以支持什么系统设计**：在合适时机主动呈现触发线索（提醒/环境提示）以提升可及性。
- **可以采集什么数据**：提醒呈现-任务启动的时间差、线索命中率。
- **可以形成什么 User State**：`cue_responsiveness`、`startup_latency`。
- **可以作为哪一部分**：Rule（在预测线索时段推送）；Statistical Model（启动概率 = f(线索可及性)）。
- **推荐优先级**：⭐⭐⭐⭐

### [12] The Subgoal Learning Model（Catrambone, 1998）

- **研究问题**：如何设计示例（worked examples）让学习者形成子目标，从而能解决需要变式的新问题？
- **核心理论**：子目标学习模型；示例中把若干步骤分组并加标签，促使学习者自我解释「这组步骤的目的」，形成以子目标组织的程序表征。
- **Independent Variables**：示例中是否给步骤组加标签、标签抽象程度（抽象 vs 表层）。
- **Dependent Variables**：解题表现、口头报告中的子目标组织、迁移到新问题。
- **主要结论**：标签帮助形成子目标；**抽象标签**比表层标签更能形成与表面特征解耦的子目标；子目标帮助学习者在「同子目标但需新步骤」的新问题上聚焦要修改的步骤。
- **结论的证据强度**：高（4 个实验，被引约 322）。
- **研究局限**：以数学/程序性任务为主；标签需领域专家设计。
- **与本项目的关系**：为「拆解不只是切分，还要给层级命名」提供依据——子目标标签是提升迁移与执行清晰度的关键设计要素。
- **可以支持什么系统设计**：Task Generator 输出的任务树应带**抽象子目标名**，而非只有原始步骤列表；LLM 负责命名。
- **可以采集什么数据**：任务树深度、子目标命名、用户对子目标的编辑。
- **可以形成什么 User State**：`mental_model_quality`（由行为代理）。
- **可以作为哪一部分**：LLM Harness（生成抽象子目标标签）；Rule（任务树不得只有叶子步骤）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [13] Subgoal-Labeled Instructional Material Improves Performance and Transfer（Margulieux 等, 2012）

- **研究问题**：子目标标注的示例材料能否降低认知负荷、促进心理模型形成并提升新任务迁移？
- **核心理论**：子目标学习 + 认知负荷/心理模型；新手难以自行建立心理模型，子目标标注可降低无关负荷。
- **Independent Variables**：是否使用子目标标注材料（+ 脚手架）。
- **Dependent Variables**：新任务表现（迁移）、心理模型建立。
- **主要结论**：子目标标注材料提升了新手在**新任务**上的表现，支持其促进心理模型与迁移。
- **结论的证据强度**：中高（受控实验，被引约 150）。
- **研究局限**：Android App Inventor 场景；样本为学生。
- **与本项目的关系**：支持「**给用户看带子目标标签的计划**」比给一堆平铺步骤更利于执行与迁移。
- **可以支持什么系统设计**：任务详情页按子目标分组展示步骤；对相似任务复用子目标结构。
- **可以采集什么数据**：任务查看行为、步骤完成顺序、重复任务的速度变化。
- **可以形成什么 User State**：`task_familiarity`。
- **可以作为哪一部分**：LLM Harness（分组标注）；Statistical Model（熟悉度→耗时）。
- **推荐优先级**：⭐⭐⭐⭐

### [14] Subgoals, Context, and Worked Examples in Learning Computing Problem Solving（Morrison 等, 2015）

- **研究问题**：在 CS 入门任务中，「给出子目标标签」与「要求学习者自己生成子目标标签」哪个更有效？
- **核心理论**：子目标学习 + 认知负荷；强调不同学科可能有不同的认知需求。
- **Independent Variables**：子目标标签的给予方式（被动接收 vs 主动生成）× 其他材料特征。
- **Dependent Variables**：任务表现增益。
- **主要结论**：结果**混合**——先前在数学/科学中的子目标标签增益在 CS 入门任务中**未能稳定复现**；CS 可能需要不同的子问题解决方式或产生不同的认知负荷。
- **结论的证据强度**：中（受控实验，被引约 174，结论为部分负向）。
- **研究局限**：单次任务、样本与任务特定；结论为「未复现」而非否证。
- **与本项目的关系**：重要的**边界条件**——不能假设子目标标注在所有任务类型上都有效；不同任务类型的粒度/呈现方式需要差异化。
- **可以支持什么系统设计**：对不同任务类型（编程 vs 写作 vs 计算）采用不同的拆解呈现；上线后 A/B 验证。
- **可以采集什么数据**：任务类型 × 拆解方式 × 完成率/耗时的交互。
- **可以形成什么 User State**：`task_type`、`decomposition_effectiveness`。
- **可以作为哪一部分**：Statistical Model（任务类型交互项）；Rule（按类型切换模板）。
- **推荐优先级**：⭐⭐⭐⭐（负结果与边界条件极具价值）

### [15] Reducing Withdrawal and Failure Rates in Introductory Programming with Subgoal Labeled Worked Examples（Margulieux 等, 2020）

- **研究问题**：子目标学习若贯穿整个学期，能否改善表现并降低退课/失败率？
- **核心理论**：子目标学习框架；把程序性解题拆到新手可掌握的更小片段。
- **Independent Variables**：子目标导向教学 vs 常规教学（整学期）。
- **Dependent Variables**：测验/考试成绩、成绩方差、退课与失败率、开放式解题过程描述。
- **主要结论**：子目标组在**形成性测验**上表现更好（总结性考试未显著更好）；但子目标组考试**方差更小**、**退课/失败人数更少**；并识别了受益的高风险学习者特征。
- **结论的证据强度**：高（整学期准实验，265 名学生，被引约 84）。
- **研究局限**：非完全随机；单课程情境。
- **与本项目的关系**：直接支持「**子目标化可降低放弃/失败风险**」——即使不一定提升峰值成绩，也能稳定尾部风险，这对计划系统极具价值。
- **可以支持什么系统设计**：对高放弃风险用户优先使用子目标化任务呈现；用子目标学习降低任务启动/延续失败。
- **可以采集什么数据**：子任务完成序列、放弃点、失败/中止事件。
- **可以形成什么 User State**：`dropout_risk`、`subgoal_completion_rate`。
- **可以作为哪一部分**：Rule（高风险用户强制子目标化）；Statistical Model（放弃风险 = f(粒度, 历史)）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [16] Learnersourcing Subgoal Labels for How-to Videos（Weir 等, 2015）

- **研究问题**：能否让学习者在学习过程中顺带产出高质量的子目标标签？
- **核心理论**：子目标标注 + learnersourcing（众包学习产出）。
- **Independent Variables**：learnersourcing 工作流 vs 无。
- **Dependent Variables**：子目标标签质量（与专家对比）、学习体验。
- **主要结论**：多数学习者生成的子目标质量可与专家生成相当；学习者称系统有助理解材料，工作流未损害学习体验。
- **结论的证据强度**：中高（实地部署 + 质量评估，被引约 89）。
- **研究局限**：限于入门网页编程视频；质量评审标准。
- **与本项目的关系**：为系统提供**低成本获得子目标标注**的路径——可让用户校正/生成 AI 的拆解，同时提升用户参与。
- **可以支持什么系统设计**：允许用户重命名/重划子目标；把用户修正回流为训练/提示数据。
- **可以采集什么数据**：用户对子目标的修改、命名文本、确认/拒绝。
- **可以形成什么 User State**：`decomposition_preference`、`label_quality`。
- **可以作为哪一部分**：LLM Harness（结合用户修正迭代）；Rule（用户覆盖优先）。
- **推荐优先级**：⭐⭐⭐⭐

### [17] AlgoSolve: Supporting Subgoal Learning with Learnersourced Microtasks（Choi 等, 2022）

- **研究问题**：能否用「学习者众包的微任务」缓解专家子目标标签稀缺，并提升学习者的解题计划质量？
- **核心理论**：子目标学习 + 微任务众包；先设计解题计划再编码。
- **Independent Variables**：AlgoSolve 工作流 vs 基线子目标学习方法。
- **Dependent Variables**：生成标签的质量、解题计划的完整度。
- **主要结论**：63 名新手被试中，AlgoSolve 帮助学习者产出更高质量标签与更完整解题计划。
- **结论的证据强度**：中高（被试间实验，被引约 10）。
- **研究局限**：算法题场景、样本较小、短期。
- **与本项目的关系**：证明**用微任务形式收集/生成子目标**可行，对系统的「任务拆解众包/校验」与「把拆解本身微任务化」有直接启发。
- **可以支持什么系统设计**：把「确认/完善拆解」做成轻量微任务；低质量子目标自动请求修正。
- **可以采集什么数据**：微任务吞吐、标签质量、修正次数。
- **可以形成什么 User State**：`decomposition_quality`、`contribution_willingness`。
- **可以作为哪一部分**：ML/Statistical Model（标签质量预测）；LLM Harness。
- **推荐优先级**：⭐⭐⭐（较新、样本小，但方向契合）

### [18] The Goal-Gradient Hypothesis Resurrected（Kivetz, Urminsky & Zheng, 2006）

- **研究问题**：人类是否也随目标接近而增加努力（目标梯度）？「进度错觉」能否加速行为？
- **核心理论**：目标梯度假设；努力投入是「原始距离剩余比例」的函数。
- **Independent Variables**：到奖励目标的距离/进度比例、是否给予「预置进度」错觉。
- **Dependent Variables**：购买频率、评分次数/访问频率、完成速度、留存与再参与。
- **主要结论**：越接近奖励，行为越频繁/越坚持；**进度错觉**（12 格卡先给 2 个「奖励」章）使人更快完成；目标梯度更强的人留存更高、再参与更快；用 goal-distance 模型统一解释。
- **结论的证据强度**：高（实地实验 + 二手数据 + 实验，被引约 565）。
- **研究局限**：消费/忠诚度情境，非工作任务；但机制与任务进度共通。
- **与本项目的关系**：支撑「**可视化进度与剩余量**能提升完成率」；提示系统应让子目标进度可见、并可在合理范围内使用「初始进度」设计。
- **可以支持什么系统设计**：任务/项目进度条、剩余子目标计数；对长目标提供进度可视化。
- **可以采集什么数据**：任务完成率随进度位置的变化、会话间隔。
- **可以形成什么 User State**：`goal_gradient_sensitivity`。
- **可以作为哪一部分**：Statistical Model（完成概率 = f(进度比例)）；LLM Harness（进度文案）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [19] The Endowed Progress Effect（Nunes & Drèze, 2006）

- **研究问题**：人为赋予的初始进展能否提高完成奖励计划的努力？
- **核心理论**：目标梯度 + 进度错觉（endowed progress）。
- **Independent Variables**：初始「已获得」进度（如 12 格卡预送 2 格）vs 无预送（10 格卡）。
- **Dependent Variables**：完成计划的比率/速度。
- **主要结论**：被赋予初始进展的顾客完成速度显著更快。（原始摘要未开放；结论以该文被广泛引用的核心发现为准，Crossref 元数据已核验。）
- **结论的证据强度**：高（经典实地实验，被引约 211；摘要不可得）。
- **研究局限**：消费场景；伦理上「虚假进度」需谨慎。
- **与本项目的关系**：支持系统用「已完成/已有基础」的框架呈现长目标，降低启动阻力（注意不得误导）。
- **可以支持什么系统设计**：把已完成的准备性工作计入进度展示；对新项目给「起步阶段已完成 X」的正向框架。
- **可以采集什么数据**：进度展示方式 × 启动率。
- **可以形成什么 User State**：`progress_framing_sensitivity`。
- **可以作为哪一部分**：Rule（进度文案模板）；LLM Harness。
- **推荐优先级**：⭐⭐⭐（摘要不可得；机制与 [18] 重叠）

### [20] Dynamics of Multiple-Goal Pursuit（Louro, Pieters & Zeelenberg, 2007）

- **研究问题**：在多目标情境中，个体何时加力、滑行、放弃或切换目标？
- **核心理论**：多目标追求模型；情绪（由先前进展产生）× 未来目标接近度共同决定努力分配，期望变化为近端机制。
- **Independent Variables**：先前目标进展、到未来目标的接近度、情绪效价。
- **Dependent Variables**：努力分配、目标切换/放弃、期望。
- **主要结论**：正负情绪对目标行为的影响方向取决于到目标的距离；研究**修正**了简单目标梯度假设；给出多目标动力学的预测。
- **结论的证据强度**：高（纵向日记 + 2 个实验，被引约 474）。
- **研究局限**：以消费/个人目标为主；目标数量有限。
- **与本项目的关系**：对 Scheduler 至关重要——**多任务/多目标并存时，接近度与情绪会改变投入**；排程应避免让多个目标同时处于「远且难」的状态。
- **可以支持什么系统设计**：多目标排程时保证至少一个目标处于「近期可达成」区间；在用户受挫时提供切换/降级。
- **可以采集什么数据**：跨目标的完成进度、切换/放弃事件、情绪自评。
- **可以形成什么 User State**：`goal_proximity`、`affect_state`、`goal_switching_tendency`。
- **可以作为哪一部分**：Statistical Model（努力/完成 = f(接近度, 情绪)）；Rule（多目标接近度平衡）。
- **推荐优先级**：⭐⭐⭐⭐⭐

### [21] Consumer Well-Being: Effects of Subgoal Failures and Goal Importance（Devezer 等, 2013）

- **研究问题**：单次子目标失败如何影响对总目标的承诺与后续行为？总目标重要性是否调节？
- **核心理论**：目标层级；子目标失败→总目标承诺下降。
- **Independent Variables**：子目标失败（单次/多次）× 总目标重要性（含可视化、自我相关性、厌恶后果）。
- **Dependent Variables**：对总目标的承诺、未来意向。
- **主要结论**：当人们认为总目标不重要时，**即使一次子目标失败也会降低对总目标的承诺**并削弱后续行为意向；目标重要性起调节作用，且重要性可被营销/设计手段驱动。
- **结论的证据强度**：中高（4 个实验、3 个情境，被引约 101）。
- **研究局限**：消费行为情境；非工作任务。
- **与本项目的关系**：重要风险提示——**任务拆解后若子任务失败，会反噬大目标承诺**；系统需保护失败子任务对整体动机的破坏，强化目标重要性。
- **可以支持什么系统设计**：子任务失败后提供「不是总目标失败」的重构；定期强化 why/目标重要性。
- **可以采集什么数据**：子任务失败事件后的下一任务启动、自报承诺变化。
- **可以形成什么 User State**：`goal_importance`、`failure_recovery`。
- **可以作为哪一部分**：Rule（失败后触发动机修复流程）；LLM Harness（重构话术）。
- **推荐优先级**：⭐⭐⭐⭐（系统风险控制）

### [22] Small Wins: Redefining the Scale of Social Problems（Weick, 1984）

- **研究问题**：面对庞大复杂问题，「小胜」策略为何有效？
- **核心理论**：小胜（small wins）；把大问题重定义为一系列可完成的小步骤，产生可控、可逆、可累积的进展。
- **Independent Variables**：问题尺度重构（整体 vs 小步）。
- **Dependent Variables**：行动启动、持续、问题解决进展。
- **主要结论**：小胜通过降低问题的吓阻性、产生可观察进展、允许学习与修正来推动解决。（原始摘要未开放；结论以该文核心命题为准。）
- **结论的证据强度**：中高（经典概念性/案例论文，被引约 740；摘要不可得）。
- **研究局限**：非量化实验；概念性证据。
- **与本项目的关系**：经典理论支撑「**把大目标切小以克服启动/拖延**」，与 [4][5][15] 的量化证据互补。
- **可以支持什么系统设计**：Task Generator 面向大目标默认产出「首个小胜」任务；奖励早期进展。
- **可以采集什么数据**：首任务启动率、早期完成率。
- **可以形成什么 User State**：`small_wins_progress`。
- **可以作为哪一部分**：Rule（大任务强制首步小胜）；LLM Harness。
- **推荐优先级**：⭐⭐⭐⭐（概念基石；摘要不可得）

### [23] Allocating Time to Future Tasks: The Effect of Task Segmentation on Planning Fallacy Bias（Forsyth & Burt, 2008）

- **研究问题**：把单一任务拆成子任务后分别估时，是否改变总时间分配/规划谬误？
- **核心理论**：规划谬误 + 任务分段（segmentation effect）。
- **Independent Variables**：任务呈现方式（整体单任务 vs 拆成子任务分别估时）。
- **Dependent Variables**：时间分配估计（单任务 vs 子任务之和）。
- **主要结论**：3 个实验中，**单任务估时显著小于子任务估时之和**（segmentation effect）；用时间线刻度估计也无法用「圆整近似」解释该效应；讨论其与规划谬误的关系及降低偏差的途径。
- **结论的证据强度**：中高（3 个实验，被引约 32）。
- **研究局限**：时间分配范式，非真实执行；样本为一般成人。
- **与本项目的关系**：**直接连接方向3与方向4**——拆解会改变估时，且通常使估计更大（更接近现实）。这为 Duration Predictor 的「是否拆解」特征提供依据。
- **可以支持什么系统设计**：Duration Predictor 在任务被拆解时应基于子任务估时之和；拆解本身作为估时校准信号。
- **可以采集什么数据**：拆解前后估时差、子任务估时 vs 实际。
- **可以形成什么 User State**：`estimation_bias`、`segmentation_effect_size`。
- **可以作为哪一部分**：Statistical Model（估时特征：是否拆解、子任务数）；Rule（大任务先拆再估）。
- **推荐优先级**：⭐⭐⭐⭐⭐（跨方向关键证据）

### [24] On the Criteria to be Used in Decomposing Systems into Modules（Parnas, 1972）

- **研究问题**：把系统拆成模块时，依据什么标准才能获得灵活性、可理解性与更短开发时间？
- **核心理论**：信息隐藏（information hiding）作为模块化准则；反对按处理步骤（flowchart）分解。
- **Independent Variables**：分解准则（按步骤 vs 按信息隐藏）。
- **Dependent Variables**：灵活性、可理解性、开发时间（概念论证 + 设计问题示例）。
- **主要结论**：分解的有效性取决于**分解准则**；以信息隐藏为准则的非常规分解在灵活性/可理解性上更优，但按传统「模块=子程序」实现可能较低效，需替代实现方式。
- **结论的证据强度**：高（软件工程奠基性论文，被引约 4713；以论证/案例为主，非实验）。
- **研究局限**：软件系统分解，非人类任务；无量化实验。
- **与本项目的关系**：为「如何判断是否继续拆解」提供经典原则——**按耦合/依赖边界拆，而非按步骤流水拆**；拆到信息独立单元即可。
- **可以支持什么系统设计**：LLM Harness 按「可独立完成的交付物/知识边界」拆解，而非机械切步骤；避免过细切分导致协调成本。
- **可以采集什么数据**：任务间依赖数、返工/协调事件。
- **可以形成什么 User State**：`task_coupling`、`coordination_cost`。
- **可以作为哪一部分**：Rule（拆解边界准则）；LLM Harness（prompt 约束）。
- **推荐优先级**：⭐⭐⭐⭐（原则性，跨域迁移）

### [25] Hierarchical Planning as Method for Task Analysis: Office Task Analysis（Sebillotte, 1988）

- **研究问题**：人类办公室任务能否用层级规划来描述？存在多少层抽象、能否归并？
- **核心理论**：AI 层级规划用于任务分析；任务可从最抽象表述逐层分解到基本动作。
- **Independent Variables**：133 个办公室任务的抽象层级结构。
- **Dependent Variables**：任务的层级描述与可归并层次。
- **主要结论**：不同任务的抽象层级数不同；可归纳出一个**四层模型**：任务表述 → 专家层（情境特定子任务）→ 最高公共层（领域无关公共程序）→ 最低可言语化层（基本动作）；公共程序可作为计算机辅助系统的功能单元。
- **结论的证据强度**：中高（133 个任务的系统性任务分析，被引约 53）。
- **研究局限**：办公室/文书任务；年代较早，技术情境不同。
- **与本项目的关系**：提供「**任务应拆到哪一层**」的经验锚点：拆到可言语化的基本动作以上、以公共子程序为执行单元；直接可用于判断是否继续拆解。
- **可以支持什么系统设计**：Task Generator 采用 3–4 层结构；以「领域无关的可执行子程序」为叶子层，避免无限下钻。
- **可以采集什么数据**：任务层级深度、叶子任务类型、执行单元复用率。
- **可以形成什么 User State**：`task_depth`、`decomposition_granularity`。
- **可以作为哪一部分**：Rule（层级深度上限/叶节点标准）；LLM Harness。
- **推荐优先级**：⭐⭐⭐⭐⭐（直接回答「拆到多细」）

### [26] Separating the Knowledge Layers: Cognitive Analysis of Search Knowledge Through Hierarchical Goal Decompositions（Bhavnani & Bates, 2002）

- **研究问题**：如何用层级目标分解显式化信息检索任务在各抽象层所需的知识？
- **核心理论**：层级目标分解作为认知任务分析方法，从 task layer 到 keystroke layer 逐层揭示所需知识。
- **Independent Variables**：任务分解的层级。
- **Dependent Variables**：各层知识（关键策略、专家/新手差异）；可检验的行为预测。
- **主要结论**：层级目标分解能定位**中间层的关键策略**（专家掌握而新手难获得），并给出基于知识获得的行为预测；可指导系统与训练设计。
- **结论的证据强度**：中高（认知任务分析方法 + 案例，被引约 27）。
- **研究局限**：检索任务；方法论为主。
- **与本项目的关系**：说明拆解的价值在于**暴露中间层策略**——AI 拆解应显式给出「怎么做」的中间层知识，而不只是首尾。
- **可以支持什么系统设计**：对新手任务补充中间层策略提示；对专家压缩中间层。
- **可以采集什么数据**：用户在各层的错误/求助、完成任务路径。
- **可以形成什么 User State**：`user_skill`（分层）、`strategy_knowledge`。
- **可以作为哪一部分**：LLM Harness（按 skill 调整中间层详细度）；Rule（新手补中间层）。
- **推荐优先级**：⭐⭐⭐⭐

### [27] Hierarchical Reinforcement Learning with the MAXQ Value Function Decomposition（Dietterich, 2000）

- **研究问题**：如何用子任务层级分解来加速强化学习并约束策略搜索？
- **核心理论**：MAXQ 值函数分解；将目标 MDP 分解为子 MDP 层级，子目标由设计者/程序识别。
- **Independent Variables**：给定的子任务层级与子目标。
- **Dependent Variables**：学习效率、策略质量（递归最优）、可用的状态抽象。
- **主要结论**：给定子目标层级可**约束策略空间、实现状态抽象**并显著加速学习；给出表示能力的形式化结果与安全使用状态抽象的五个条件。
- **结论的证据强度**：高（形式化证明 + 实验，JAIR，被引约 1456）。
- **研究局限**：依赖人类预先指定有用子目标；非人类执行场景。
- **与本项目的关系**：为「**子目标层级本身就是一种降维/加速机制**」提供形式化依据；也说明「如何判断是否继续拆解」可视为「是否引入有用子目标以约束解空间」。
- **可以支持什么系统设计**：Task Generator 为 LLM/规划器提供层级模板以约束搜索；避免无意义下钻。
- **可以采集什么数据**：层级对规划成功率/步数的影响。
- **可以形成什么 User State**：—（系统侧结构而非用户状态）。
- **可以作为哪一部分**：LLM Harness（层级约束）；Rule（层级模板）。
- **推荐优先级**：⭐⭐⭐⭐（理论/机制）

### [28] Task Decomposition and Newsvendor Decision Making（Lee & Siemsen, 2017）

- **研究问题**：把决策拆成「点预测 / 不确定性估计 / 服务水平决策」等步骤，是否总能改善决策？
- **核心理论**：任务分解在组织中的常见做法；分解收益依赖情境。
- **Independent Variables**：直接决策 vs 分解式决策；关键比率（<50% 与否）；需求不确定性高低；是否有决策支持。
- **Dependent Variables**：订货决策绩效。
- **主要结论**：分解常带来改善，**但当关键比率 <50% 或不确定性过高时，分解可能反而更差**（服务水平设得过高或随机判断误差过大）；**若同时提供建议数量，分解总体更优**——分解与决策支持是互补的。
- **结论的证据强度**：高（3 个行为实验，Management Science，被引约 96）。
- **研究局限**：报童问题（库存决策）情境，非通用任务。
- **与本项目的关系**：极重要边界条件——**拆解并非总是有益**；当情境（不确定性/参数）不利或用户能力不足时，需配合系统建议。直接回答「任务过大 vs 过细」的权衡。
- **可以支持什么系统设计**：LLM Harness 拆解时同时给出建议步骤/默认值；对高不确定性任务不要盲目细分。
- **可以采集什么数据**：任务不确定性、拆解方式 × 完成质量。
- **可以形成什么 User State**：`decomposition_benefit`（情境依赖）。
- **可以作为哪一部分**：Rule（何时拆/不拆）；Statistical Model（拆解收益预测）。
- **推荐优先级**：⭐⭐⭐⭐⭐（回答核心权衡问题）

### [29] An Approach to Training Based upon Principled Task Decomposition（Frederiksen & White, 1989）

- **研究问题**：如何基于有原则的任务分解来设计训练，使复杂技能可教？
- **核心理论**：原则性任务分解（principled task decomposition）；把复杂技能分解为可训练的组件。
- **Independent Variables**：任务分解方案。
- **Dependent Variables**：训练效果/技能获得。
- **主要结论**：有原则的分解可支持复杂技能的系统训练。（原始摘要未开放；结论以题名与该文定位为准，建议核对原文。）
- **结论的证据强度**：中（期刊论文，被引约 138；摘要不可得）。
- **研究局限**：年代较早；摘要不可得；情境为电子故障排查训练。
- **与本项目的关系**：为「按原则而非随意拆解」提供教育学证据，支持 Task Generator 的结构化拆解。
- **可以支持什么系统设计**：训练型任务按组件-整合顺序拆解。
- **可以采集什么数据**：组件任务完成→整体任务完成的迁移。
- **可以形成什么 User State**：`component_mastery`。
- **可以作为哪一部分**：Rule（拆解模板）；LLM Harness。
- **推荐优先级**：⭐⭐⭐（摘要不可得）

### [30] Acquiring Skill at Mental Calculation in Adulthood: A Task Decomposition（Charness & Campbell, 1988）

- **研究问题**：成年人mental calculation 技能的获得，能否通过任务分解刻画？
- **核心理论**：任务分解分析技能成分（如检索、计算策略）。
- **Independent Variables**：问题类型/策略。
- **Dependent Variables**：反应时、错误率、策略报告。
- **主要结论**：心算技能由可分解的成分与策略构成，练习改变成分效率。（原始摘要未开放；结论以题名与该文在技能获得文献中的定位为准。）
- **结论的证据强度**：中（实验，被引约 128；摘要不可得）。
- **研究局限**：心算任务；摘要不可得。
- **与本项目的关系**：说明**不同类型的任务其可分解的「最小单元」不同**（认知检索 vs 动作步骤），支持按任务类型差异化粒度。
- **可以支持什么系统设计**：Task Generator 按任务类型选择分解模板（认知型/程序型/创造型）。
- **可以采集什么数据**：任务类型标签、成分耗时。
- **可以形成什么 User State**：`task_type`、`component_time`。
- **可以作为哪一部分**：Statistical Model（任务类型 → 粒度/耗时特征）。
- **推荐优先级**：⭐⭐⭐（摘要不可得）

### [31] The Magical Number 4 in Short-Term Memory: A Reconsideration of Mental Storage Capacity（Cowan, 2001）

- **研究问题**：短时记忆的容量上限到底是多少？如何界定可靠观测的条件？
- **核心理论**：工作记忆/短时记忆容量有限；提出约 **4 个组块**的中央容量上限。
- **Independent Variables**：信息负载、组块条件、阻止复述/长时记忆的策略。
- **Dependent Variables**：记忆容量估计、绩效不连续点。
- **主要结论**：在排除复述与长时记忆辅助等条件下，容量上限平均约 4 个组块；给出可识别组块与容量上限的四类条件。
- **结论的证据强度**：高（权威靶文 + 同行评论，被引约 6910）。
- **研究局限**：实验室记忆任务；组块大小依领域知识变化。
- **与本项目的关系**：为「**一次呈现/一次执行的任务步数上限**」提供认知容量锚点——单屏/单步任务清单不宜超过约 4 个组块，否则应继续分组或用层级。
- **可以支持什么系统设计**：任务清单分页/分组（每组 3–4 项）；LLM Harness 输出分组结构。
- **可以采集什么数据**：单屏任务数 × 完成率/错误率。
- **可以形成什么 User State**：`working_memory_load`（任务侧代理）。
- **可以作为哪一部分**：Rule（单组任务数上限）；LLM Harness（分组）。
- **推荐优先级**：⭐⭐⭐⭐

### [32] Neural Mechanisms of Hierarchical Planning in a Virtual Subway Network（Balaguer 等, 2016）`[fMRI]`

- **研究问题**：人脑如何表征层级计划以降低规划计算成本？
- **核心理论**：层级强化学习/层级规划；状态可聚类为「上下文」以高效表征。
- **Independent Variables**：虚拟地铁网络中的规划任务结构。
- **Dependent Variables**：行为上的层级执行证据；fMRI 活动（背内侧前额叶、前运动皮层）随层级表征成本变化；上下文与上下文切换的神经信号。
- **主要结论**：**行为证据显示人类执行层级化计划**；神经活动与层级计划表征成本及上下文/上下文切换信号一致。
- **结论的证据强度**：中高（fMRI 实验，Neuron，被引约 192；依赖实验室设备）。
- **研究局限**：依赖 fMRI、虚拟地铁任务；不能直接外推到现实工作任务。
- **与本项目的关系**：提供「层级计划是降低认知成本的生物性策略」的理论价值，支持系统采用层级而非平铺的任务结构。
- **可以支持什么系统设计**：任务树/分组执行的界面隐喻；上下文切换代价的启发式。
- **可以采集什么数据**：任务切换事件、切换后耗时/错误（行为代理）。
- **可以形成什么 User State**：`context_switch_cost`（行为代理）。
- **可以作为哪一部分**：Rule（减少不必要上下文切换的排程）；LLM Harness（层级结构）。
- **推荐优先级**：⭐⭐⭐（理论价值高，设备依赖需标记）

### [33] A Neural Signature of Hierarchical Reinforcement Learning（Ribas-Fernandes 等, 2011）`[fMRI]`

- **研究问题**：大脑是否用层级强化学习（HRL）机制来组织子任务？子目标是否产生类似奖励预测误差的信号？
- **核心理论**：层级强化学习；除总体目标外，**子目标**也应产生奖励预测误差。
- **Independent Variables**：任务层级结构与子目标达成事件。
- **Dependent Variables**：fMRI 预测误差相关信号。
- **主要结论**：3 项神经影像研究中观察到与**子目标相关奖励预测误差**一致的反应，位于既有强化学习相关脑区；支持 HRL 对层级行为神经过程的解释力。
- **结论的证据强度**：中高（3 个 fMRI 研究，Neuron，被引约 134；依赖实验室设备）。
- **研究局限**：fMRI；实验室任务；神经信号非直接可采集于本项目。
- **与本项目的关系**：为「**子目标达成本身具有强化价值**」提供神经科学依据，支持系统对子目标完成给予即时反馈/奖励。
- **可以支持什么系统设计**：子任务完成时即时反馈/微奖励；进度可视化。
- **可以采集什么数据**：子任务完成事件、完成后的继续行为。
- **可以形成什么 User State**：`subgoal_reward_sensitivity`。
- **可以作为哪一部分**：Rule（子目标即时反馈）；Statistical Model（完成率随子目标奖励变化）。
- **推荐优先级**：⭐⭐⭐（理论价值；设备依赖标记）

### [34] Task Aversiveness and Procrastination（Blunt & Pychyl, 2000）

- **研究问题**：任务厌恶感的维度结构如何？它与拖延在个人项目的不同阶段有何关系？
- **核心理论**：任务厌恶的多维构念（如无聊、挫折、技能不足、努力、模糊等）；任务厌恶驱动拖延。
- **Independent Variables**：任务厌恶各维度、项目阶段。
- **Dependent Variables**：拖延水平。
- **主要结论**：任务厌恶是多维的，且与拖延相关，不同维度/阶段关系不同。（原始摘要未开放；结论以题名与该文的核心论点为准，具体维度需查原文。）
- **结论的证据强度**：中高（实证研究，被引约 180；摘要不可得）。
- **研究局限**：自评、相关设计；摘要不可得。
- **与本项目的关系**：直接支撑「**任务过大/模糊/枯燥会增加拖延**」，即拆解应降低任务的模糊性与单步厌恶感（把大而模糊的任务变成小而具体的子任务）。
- **可以支持什么系统设计**：拆解时消除模糊措辞、降低单任务所需首次投入；对高厌恶任务优先拆小并搭配进度反馈。
- **可以采集什么数据**：任务推迟事件、任务属性（模糊度、所需努力）、自评厌恶。
- **可以形成什么 User State**：`task_aversiveness`、`procrastination_risk`。
- **可以作为哪一部分**：Statistical Model（完成率 = f(厌恶, 粒度)）；Rule（高厌恶任务强制拆小）。
- **推荐优先级**：⭐⭐⭐⭐

---

## 四、对本项目重点问题的综合回答（基于上述采纳文献）

1. **多大规模的任务粒度适合执行？** 没有单一数值，但有三个可操作锚点：(a) 单次可完成、能产生即时掌握体验的「近端子目标」（Bandura & Schunk 1981；Latham & Seijts 1999）；(b) 一次呈现约 **3–4 个组块**以内（Cowan 2001）；(c) 以「领域无关、可言语化的可执行子程序」为叶子层（Sebillotte 1988；Parnas 1972）。
2. **子目标能否提高完成率？** 能。近端子目标显著提升学习进度与自我效能（[4][5]）；整学期子目标化虽不提高峰值成绩，但**降低成绩方差与退课/失败率**（[15]）；子目标达成具有内在强化价值（[33]）且触发目标梯度加速（[18][19]）。
3. **任务过大增加拖延、过细增加管理成本？** 大/模糊任务增加厌恶与拖延（[34]），只给远端目标甚至不如「尽力而为」（[5]）。但拆解并非总是有益：当不确定性过高或参数不利时，分解反而降低决策质量（[28]）；软件工程也警示按步骤细切会增加耦合/实现成本（[24]）。**结论：拆到「可按边界独立完成」即可，需配合建议与默认值。**
4. **如何判断是否继续拆解？** 依据：(a) 子任务是否可由用户独立完成/是否能形成承诺（[1][3]）；(b) 是否已到达可言语化的基本执行单元（[25]）；(c) 是否引入有用子目标以约束搜索、降低认知成本（[27][32]）；(d) 拆解是否显著改变估时并接近现实（[23]）；(e) 任务类型是否需要先学习（[6]）。
5. **不同任务类型的粒度差异？** 需要先获取知识的任务应使用**学习子目标**（[6]）；CS/编程任务的子目标标注效应与数学/科学不同，呈混合结果（[14]）；心算等认知任务与程序型任务的可分解单元不同（[30]）；检索类任务的价值在中间层策略（[26]）。**结论：粒度/目标形式须按任务类型参数化，不能一刀切。**

## 五、可复核性说明

- 所有采纳文献的 DOI 均通过 Crossref `works/{DOI}` 实时核验，快照保存于 `api/verify/*.json`（含 `DIGEST.txt`）。
- 关键词命中、去重候选与相关性排序分别见 `api/candidates_03.txt`、`api/ranked_03.txt`；采纳文献摘要见 `api/selected_abstracts_03.txt` 与 `api/abstracts.json`。
- 标注「原始摘要未开放」的条目（[1][7][19][22][29][30][34] 等），其结论仅依据题名与该文可核验的题录信息，未做超出证据的推断，建议获取全文后再细化。
