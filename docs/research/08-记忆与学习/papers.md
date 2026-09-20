# 方向8：学习、记忆与复习（Learning, Memory & Review）文献调研

> **检索 361 篇（去重后可核验记录），采纳 31 篇。**
>
> - 检索时间：2026-09-19
> - 检索 API：Europe PMC REST（覆盖 MEDLINE/PubMed）、NCBI PubMed E-utilities、Crossref REST、Semantic Scholar Graph API（限流，仅少量命中）
> - 原始检索数据：本目录 `./api/`（含 `epmc_*.json`、`pubmed_*.json`、`crossref_*.json`、`_verified_titles_*.json`、`_citation_meta.json`、`_abstracts_dump.txt`）
> - 筛选原则：优先 peer-reviewed / meta-analysis / 高质量会议；优先变量可被系统观测；依赖 EEG/fMRI/实验室设备者已标记。
> - **可信度声明**：本清单每一条均由上述 API 实际返回，并经 Crossref/Europe PMC 按 DOI 或精确题名二次核验（`_citation_meta.json` 记录了卷期页码）。中文关键词（遗忘曲线、间隔重复、间隔效应、检索练习、学习保持、自适应学习）已尝试检索，但 CNKI/万方无公开机检 API，故未纳入中文数据库记录。
> - 因误检被剔除的典型噪声：材料科学/生物信息学中同名词（如 `spacing effect` 命中混凝土/基因间距等）已在筛选中排除。

---

## 一、GB/T 7714 编号引用清单

[1] CEPEDA N J, PASHLER H, VUL E, et al. Distributed practice in verbal recall tasks: A review and quantitative synthesis[J]. Psychological Bulletin, 2006, 132(3): 354-380. DOI:10.1037/0033-2909.132.3.354.

[2] ROEDIGER H L, KARPICKE J D. Test-enhanced learning: Taking memory tests improves long-term retention[J]. Psychological Science, 2006, 17(3): 249-255. DOI:10.1111/j.1467-9280.2006.01693.x.

[3] ROEDIGER H L, KARPICKE J D. The power of testing memory: Basic research and implications for educational practice[J]. Perspectives on Psychological Science, 2006, 1(3): 181-210. DOI:10.1111/j.1745-6916.2006.00012.x.

[4] PASHLER H, ROHRER D, CEPEDA N J, et al. Enhancing learning and retarding forgetting: Choices and consequences[J]. Psychonomic Bulletin & Review, 2007, 14(2): 187-193. DOI:10.3758/bf03194050.

[5] CEPEDA N J, VUL E, ROHRER D, et al. Spacing effects in learning: A temporal ridgeline of optimal retention[J]. Psychological Science, 2008, 19(11): 1095-1102. DOI:10.1111/j.1467-9280.2008.02209.x.

[6] KARPICKE J D, ROEDIGER H L. The critical importance of retrieval for learning[J]. Science, 2008, 319(5865): 966-968. DOI:10.1126/science.1152408.

[7] KARPICKE J D, BLUNT J R. Retrieval practice produces more learning than elaborative studying with concept mapping[J]. Science, 2011, 331(6018): 772-775. DOI:10.1126/science.1199327.

[8] DUNLOSKY J, RAWSON K A, MARSH E J, et al. Improving students' learning with effective learning techniques: Promising directions from cognitive and educational psychology[J]. Psychological Science in the Public Interest, 2013, 14(1): 4-58. DOI:10.1177/1529100612453266.

[9] ROWLAND C A. The effect of testing versus restudy on retention: A meta-analytic review of the testing effect[J]. Psychological Bulletin, 2014, 140(6): 1432-1463. DOI:10.1037/a0037559.

[10] YANG C, LUO L, VADILLO M A, et al. Testing (quizzing) boosts classroom learning: A systematic and meta-analytic review[J]. Psychological Bulletin, 2021, 147(4): 399-435. DOI:10.1037/bul0000309.

[11] LATIMIER A, PEYRE H, RAMUS F. A meta-analytic review of the benefit of spacing out retrieval practice episodes on retention[J]. Educational Psychology Review, 2021, 33(3): 959-987. DOI:10.1007/s10648-020-09572-8.

[12] MURRE J M J, DROS J. Replication and analysis of Ebbinghaus' forgetting curve[J]. PLOS ONE, 2015, 10(7): e0120644. DOI:10.1371/journal.pone.0120644.

[13] AVERELL L, HEATHCOTE A. The form of the forgetting curve and the fate of memories[J]. Journal of Mathematical Psychology, 2011, 55(1): 25-35. DOI:10.1016/j.jmp.2010.08.009.

[14] KORNELL N. Optimising learning using flashcards: Spacing is more effective than cramming[J]. Applied Cognitive Psychology, 2009, 23(9): 1297-1317. DOI:10.1002/acp.1537.

[15] BAHRICK H P, PHELPS E. Retention of Spanish vocabulary over 8 years[J]. Journal of Experimental Psychology: Learning, Memory, and Cognition, 1987, 13(2): 344-349. DOI:10.1037/0278-7393.13.2.344.

[16] UNSWORTH N. Individual differences in long-term memory[J]. Psychological Bulletin, 2019, 145(1): 79-139. DOI:10.1037/bul0000176.

[17] MURRE J M J, CHESSA A G. Power laws from individual differences in learning and forgetting: Mathematical analyses[J]. Psychonomic Bulletin & Review, 2011, 18(3): 592-597. DOI:10.3758/s13423-011-0076-y.

[18] XU Y, PRAT C S, SENSE F, et al. Default mode network connectivity predicts individual differences in long-term forgetting: Evidence for storage degradation, not retrieval failure[J]. PLOS Computational Biology, 2025, 21(9): e1013485. DOI:10.1371/journal.pcbi.1013485.

[19] LINDSEY R V, SHROYER J D, PASHLER H, et al. Improving students' long-term knowledge retention through personalized review[J]. Psychological Science, 2014, 25(3): 639-647. DOI:10.1177/0956797613504302.

[20] SETTLES B, MEEDER B. A trainable spaced repetition model for language learning[C]//Proceedings of the 54th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers). Berlin: ACL, 2016: 1848-1858. DOI:10.18653/v1/p16-1174.

[21] REDDY S, LABUTOV I, BANERJEE S, et al. Unbounded human learning: Optimal scheduling for spaced repetition[C]//Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining. New York: ACM, 2016: 1815-1824. DOI:10.1145/2939672.2939850.

[22] TABIBIAN B, UPADHYAY U, DE A, et al. Enhancing human learning via spaced repetition optimization[J]. Proceedings of the National Academy of Sciences, 2019, 116(10): 3988-3993. DOI:10.1073/pnas.1815156116.

[23] ZAIDI A, CAINES A, MOORE R, et al. Adaptive forgetting curves for spaced repetition language learning[C]//Artificial Intelligence in Education (AIED 2020), LNCS 12164. Cham: Springer, 2020: 358-363. DOI:10.1007/978-3-030-52240-7_65.

[24] XIAO Q, WANG J. DRL-SRS: A deep reinforcement learning approach for optimizing spaced repetition scheduling[J]. Applied Sciences, 2024, 14(13): 5591. DOI:10.3390/app14135591.

[25] POKRYWKA J, BIEDALAK M, GRALIŃSKI F, et al. Modeling spaced repetition with LSTMs[C]//Proceedings of the 15th International Conference on Computer Supported Education (CSEDU). Setúbal: SCITEPRESS, 2023: 88-95. DOI:10.5220/0011724000003470.

[26] REDDY S, LABUTOV I, BANERJEE S. A queueing network model for spaced repetition[C]//Proceedings of the Third (2016) ACM Conference on Learning @ Scale. New York: ACM, 2016: 289-292. DOI:10.1145/2876034.2893436.

[27] XIE H, CHU H C, HWANG G J, et al. Trends and development in technology-enhanced adaptive/personalized learning: A systematic review of journal publications from 2007 to 2017[J]. Computers & Education, 2019, 140: 103599. DOI:10.1016/j.compedu.2019.103599.

[28] KULIK J A, FLETCHER J D. Effectiveness of intelligent tutoring systems: A meta-analytic review[J]. Review of Educational Research, 2016, 86(1): 42-78. DOI:10.3102/0034654315581420.

[29] MA W, ADESOPE O O, NESBIT J C, et al. Intelligent tutoring systems and learning outcomes: A meta-analysis[J]. Journal of Educational Psychology, 2014, 106(4): 901-918. DOI:10.1037/a0037123.

[30] VANLEHN K. The relative effectiveness of human tutoring, intelligent tutoring systems, and other tutoring systems[J]. Educational Psychologist, 2011, 46(4): 197-221. DOI:10.1080/00461520.2011.611369.

[31] MAYE J, HURLEY F. The effectiveness of spaced repetition in medical education: A systematic review and meta-analysis[J]. The Clinical Teacher, 2026, 23(2). DOI:10.1111/tct.70353.

---

## 二、逐条源链接（DOI，均可解析）

| # | 标题 | 源链接 |
|---|------|--------|
| 1 | Distributed practice in verbal recall tasks | https://doi.org/10.1037/0033-2909.132.3.354 |
| 2 | Test-enhanced learning | https://doi.org/10.1111/j.1467-9280.2006.01693.x |
| 3 | The power of testing memory | https://doi.org/10.1111/j.1745-6916.2006.00012.x |
| 4 | Enhancing learning and retarding forgetting | https://doi.org/10.3758/bf03194050 |
| 5 | Spacing effects in learning | https://doi.org/10.1111/j.1467-9280.2008.02209.x |
| 6 | The critical importance of retrieval for learning | https://doi.org/10.1126/science.1152408 |
| 7 | Retrieval practice produces more learning… | https://doi.org/10.1126/science.1199327 |
| 8 | Improving students' learning with effective techniques | https://doi.org/10.1177/1529100612453266 |
| 9 | Testing versus restudy: meta-analysis | https://doi.org/10.1037/a0037559 |
| 10 | Testing (quizzing) boosts classroom learning | https://doi.org/10.1037/bul0000309 |
| 11 | Spacing out retrieval practice: meta-analysis | https://doi.org/10.1007/s10648-020-09572-8 |
| 12 | Replication and analysis of Ebbinghaus' curve | https://doi.org/10.1371/journal.pone.0120644 |
| 13 | The form of the forgetting curve | https://doi.org/10.1016/j.jmp.2010.08.009 |
| 14 | Optimising learning using flashcards | https://doi.org/10.1002/acp.1537 |
| 15 | Retention of Spanish vocabulary over 8 years | https://doi.org/10.1037/0278-7393.13.2.344 |
| 16 | Individual differences in long-term memory | https://doi.org/10.1037/bul0000176 |
| 17 | Power laws from individual differences | https://doi.org/10.3758/s13423-011-0076-y |
| 18 | DMN connectivity predicts forgetting rate | https://doi.org/10.1371/journal.pcbi.1013485 |
| 19 | Personalized review improves retention | https://doi.org/10.1177/0956797613504302 |
| 20 | Trainable spaced repetition model (HLR) | https://doi.org/10.18653/v1/p16-1174 |
| 21 | Unbounded human learning (optimal scheduling) | https://doi.org/10.1145/2939672.2939850 |
| 22 | Spaced repetition optimization (MEMORIZE) | https://doi.org/10.1073/pnas.1815156116 |
| 23 | Adaptive forgetting curves | https://doi.org/10.1007/978-3-030-52240-7_65 |
| 24 | DRL-SRS (deep RL scheduler) | https://doi.org/10.3390/app14135591 |
| 25 | Modeling spaced repetition with LSTMs | https://doi.org/10.5220/0011724000003470 |
| 26 | Queueing network model for spaced repetition | https://doi.org/10.1145/2876034.2893436 |
| 27 | Adaptive/personalized learning: systematic review | https://doi.org/10.1016/j.compedu.2019.103599 |
| 28 | Effectiveness of ITS: meta-analytic review | https://doi.org/10.3102/0034654315581420 |
| 29 | ITS and learning outcomes: meta-analysis | https://doi.org/10.1037/a0037123 |
| 30 | Human vs ITS tutoring effectiveness | https://doi.org/10.1080/00461520.2011.611369 |
| 31 | Spaced repetition in medical education: meta | https://doi.org/10.1111/tct.70353 |

---

## 三、逐篇分析模板

> 字段说明：`User State` 指可写入本项目用户状态的变量；`Rule/Statistical Model/ML/LLM Harness` 指该文献可支撑的闭环组件。标记 `⚠️ 需实验室设备` 者不可直接产品化。

### [1] Cepeda et al. (2006) — 分散练习定量综述
- **研究问题**：练习间隔（spacing gap）如何影响长期记忆保持？最优间隔与保持间隔的关系？
- **核心理论**：间隔效应（spacing effect）/ 编码变异性理论。
- **IV**：练习间隔（分钟~月）、保持间隔、材料类型。
- **DV**：回忆/再认正确率。
- **主要结论**：分散练习显著优于集中练习；最优间隔随目标保持期增长而增长（约保持期的 10–20%）。
- **结论证据强度**：强（定量综述，聚合大量实验，效应稳健）。
- **研究局限**：以言语材料为主；实验室任务多；个体差异未建模。
- **与本项目关系**：Review Scheduler 的核心理论依据——复习间隔应随"距考试/目标日期"动态缩放。
- **可支持的系统设计**：按目标保持期反向计算首次与后续复习间隔；间隔随剩余时间衰减。
- **可采集数据**：复习时间戳、复习间隔、复习后测试正确率、距目标日期。
- **可形成 User State**：`retention_target`、`current_interval_days`、`spacing_ratio`。
- **Rule/Model 定位**：Statistical Model（间隔—保持期回归）+ Rule（最小/最大间隔硬约束）。
- **推荐优先级**：★★★★★（必读，Scheduler 基石）。

### [2] Roediger & Karpicke (2006) — 测试增强学习
- **研究问题**：测试（提取练习）是否比重复学习更能提升长期保持？
- **核心理论**：提取练习/测试效应（testing effect）。
- **IV**：学习方式（test vs restudy）、保持间隔（5 min vs 1 周）。
- **DV**：自由回忆/再认成绩。
- **主要结论**：短期测试组略低，长期（1 周）测试组显著优于重复学习组；无需反馈即有效。
- **结论证据强度**：强（受控实验，重复验证）。
- **研究局限**：实验室短文材料；样本量小；外部效度有限。
- **与本项目关系**：复习不应只是"再看一遍"，应强制"先测后看"。
- **可支持的系统设计**：Review Scheduler 的复习单元采用 retrieval-first（先自测），失败才展示内容。
- **可采集数据**：自测结果、反应时、是否查看答案、自评把握度。
- **可形成 User State**：`recall_probability`、`last_test_score`、`retrieval_strength`。
- **Rule/Model 定位**：Rule（复习必须先测）；Statistical Model（提取结果→保持预测）。
- **推荐优先级**：★★★★★。

### [3] Roediger & Karpicke (2006) — 测试记忆的力量（综述）
- **研究问题**：测试促进学习的基础研究证据及其教育应用与负面效应。
- **核心理论**：测试效应、动态评估、形成性评价。
- **IV**：测试频率/形式、反馈有无。
- **DV**：延迟保持、迁移。
- **主要结论**：频繁测试提升各学段成绩；负面效应较小且不抵消正效应。
- **证据强度**：中—强（叙述性综述，涵盖实验室与课堂）。
- **局限**：综述非元分析；未量化边界条件。
- **与本项目关系**：支持将"测验/自测"设计为复习与进度评估的统一机制。
- **系统设计**：把复习与进度测量合并为同一交互，降低用户负担。
- **可采集数据**：测试频率、成绩轨迹。
- **User State**：`test_frequency`、`mastery_trend`。
- **定位**：Rule + LLM Harness（生成测试题）。
- **优先级**：★★★★。

### [4] Pashler et al. (2007) — 学习增强与遗忘延缓
- **研究问题**：间隔、反馈、提取练习等教学设计选择对保持/遗忘的影响。
- **核心理论**：间隔效应、提取练习、反馈学习。
- **IV**：练习间隔、反馈时点、练习形式。
- **DV**：保持期内的回忆率与遗忘速率。
- **主要结论**：间隔与提取练习有效；提取练习未必降低遗忘速率（可能只提升初始强度）；反馈并非总是必需。
- **证据强度**：中（研究纲要/综述，提出开放问题）。
- **局限**：非系统综述；部分结论待验证。
- **与本项目关系**：提醒系统区分"提升记忆强度"与"降低遗忘率"是两件事，影响参数建模。
- **系统设计**：遗忘曲线参数与初始记忆强度分开估计。
- **可采集数据**：多轮复习的成绩衰减序列。
- **User State**：`initial_strength`、`decay_rate`（分离两参数）。
- **定位**：Statistical Model。
- **优先级**：★★★★。

### [5] Cepeda et al. (2008) — 最优保持的"时间山脊"
- **研究问题**：在长达 1 年的保持期下，最优学习间隔是多少？
- **核心理论**：间隔效应与保持间隔的交互。
- **IV**：学习间隔（至 3.5 个月）、最终测试延迟（至 1 年）。
- **DV**：最终测试成绩。
- **主要结论**：最优间隔随测试延迟先升后降；最优间隔占保持期比例从 ~20–40%（1 周）降至 ~5–10%（1 年）；多数教育实践效率低。
- **证据强度**：强（N>1350，随机化，长时程）。
- **局限**：事实性知识；单次复习；未含个体差异。
- **与本项目关系**：直接给出"复习间隔比例"的可计算规则。
- **系统设计**：`optimal_gap = f(retention_interval)`，随目标临近动态调整。
- **可采集数据**：目标日期、复习间隔、最终成绩。
- **User State**：`retention_interval_days`、`optimal_gap_days`。
- **定位**：Rule + Statistical Model。
- **优先级**：★★★★★（Scheduler 直接采用）。

### [6] Karpicke & Roediger (2008) — 提取对学习的决定作用
- **研究问题**：反复学习 vs 反复测试，对长期保持的作用。
- **核心理论**：提取练习、desirable difficulty。
- **IV**：学习/测试次数组合。
- **DV**：1 周后回忆。
- **主要结论**：重复学习几乎不提升长期保持；提取练习才是关键；学习者元认知误判。
- **证据强度**：强（受控实验，Science）。
- **局限**：小样本；词汇材料。
- **与本项目关系**：复习调度应以"提取事件"为核心，而非"浏览时长"。
- **系统设计**：复习完成判定基于自测，不以阅读时长为依据。
- **可采集数据**：提取次数、提取成功率。
- **User State**：`retrieval_count`、`retrieval_success_rate`。
- **定位**：Rule。
- **优先级**：★★★★★。

### [7] Karpicke & Blunt (2011) — 提取练习 vs 概念图
- **研究问题**：提取练习与精细学习（概念图）对复杂科学概念学习的比较。
- **核心理论**：提取练习、有意义学习。
- **IV**：学习策略（提取练习/概念图/重读）。
- **DV**：即时与 1 周后的回忆、推理题。
- **主要结论**：提取练习在两类题上均优于概念图；学习者主观偏好相反。
- **证据强度**：强（实验，Science）；但存在方法学争议（见同期 Comment, DOI:10.1126/science.1203698）。
- **局限**：单篇实验；争议未决。
- **与本项目关系**：复杂任务也应自测，而非仅做整理/总结。
- **系统设计**：LLM 生成的复习任务包含"解释/推理"型自测。
- **可采集数据**：推理题得分、主观偏好。
- **User State**：`conceptual_mastery` vs `factual_mastery`。
- **定位**：LLM Harness（出题）+ Rule。
- **优先级**：★★★☆。

### [8] Dunlosky et al. (2013) — 十种学习技术效力评估
- **研究问题**：常见学习技术在不同条件下的一般化效力。
- **核心理论**：认知与教育心理学证据综合。
- **IV**：10 种学习技术、学习条件、学生特征、材料、评分任务。
- **DV**：记忆/问题解决/理解成绩。
- **主要结论**：practice testing 与 distributed practice 效力最高；highlighting、rereading 等低效。
- **证据强度**：强（系统综述/专著）。
- **局限**：多数研究在实验室；迁移证据有限。
- **与本项目关系**：为系统"推荐学习行为"提供效力排序。
- **系统设计**：计划生成优先安排 self-test 与分散练习；避免仅"阅读"任务。
- **可采集数据**：各类学习行为频次与成绩。
- **User State**：`effective_study_ratio`。
- **定位**：Rule（行为库权重）。
- **优先级**：★★★★。

### [9] Rowland (2014) — 测试效应元分析
- **研究问题**：测试 vs 重学的保持效应量及其调节变量。
- **核心理论**：提取努力、episodic context、bifurcation model。
- **IV**：测试形式（回忆/再认）、反馈、材料。
- **DV**：延迟保持。
- **主要结论**：测试效应稳健；初始回忆测试收益大于再认；对"语义精细"解释支持有限。
- **证据强度**：强（元分析）。
- **局限**：实验室研究为主；调节变量异质性。
- **与本项目关系**：量化测试效应，指导 A/B 与效应量预估。
- **系统设计**：优先安排自由回忆式自测而非选择题。
- **可采集数据**：测试格式、延迟、成绩。
- **User State**：`test_format_pref`。
- **定位**：Statistical Model（效应量）。
- **优先级**：★★★★。

### [10] Yang et al. (2021) — 课堂测验元分析
- **研究问题**：课堂测验对学业成绩的效应量、边界条件与机制。
- **核心理论**：额外暴露、迁移适宜加工、动机。
- **IV**：测验策略、对照条件、格式一致性、反馈、重复次数、时点、时长、设计。
- **DV**：学业成就。
- **主要结论**：整体 g=0.499（中等）；受反馈、格式一致性、重复次数等调节。
- **证据强度**：强（222 项研究，48,478 名学生）。
- **局限**：异质性大；发表偏倚风险。
- **与本项目关系**：课堂/真实场景中测验仍有效，可用于成人自学系统。
- **系统设计**：复习测试提供纠正性反馈、保持测试—学习格式一致。
- **可采集数据**：测验次数、反馈类型、成绩。
- **User State**：`quiz_streak`、`feedback_exposure`。
- **定位**：Rule + Statistical Model。
- **优先级**：★★★★★。

### [11] Latimier et al. (2021) — 间隔提取练习元分析
- **研究问题**：把提取练习在时间上分散是否优于集中提取？
- **核心理论**：两种 desirable difficulties（提取+间隔）叠加。
- **IV**：间隔 vs 集中提取练习、间隔长度。
- **DV**：最终保持。
- **主要结论**：间隔提取练习有稳定收益；支持两者结合。
- **证据强度**：强（29 项研究元分析）。
- **局限**：研究数量中等；间隔参数未统一。
- **与本项目关系**：直接支撑"间隔重复 + 检索练习"的联合调度。
- **系统设计**：Review Scheduler 同时优化"何时复习"与"复习时强制提取"。
- **可采集数据**：复习间隔序列、提取成绩序列。
- **User State**：`spaced_retrieval_score`。
- **定位**：Rule + Statistical Model。
- **优先级**：★★★★★。

### [12] Murre & Dros (2015) — 艾宾浩斯遗忘曲线复现
- **研究问题**：用现代方法复现并拟合艾宾浩斯遗忘曲线，检验曲线形式。
- **核心理论**：遗忘曲线；指数/幂律/对数拟合。
- **IV**：保持间隔（20 min~31 天）。
- **DV**：节省率（savings）。
- **主要结论**：遗忘曲线可由指数或幂函数良好拟合；个体内曲线稳定；与经典结论一致。
- **证据强度**：中—强（重复测量、单被试密集设计）。
- **局限**：无意义音节、单被试传统、生态效度低。
- **与本项目关系**：提供遗忘函数参数化的经验基准。
- **系统设计**：Scheduler 初始采用幂律/指数衰减先验，再由个人数据更新。
- **可采集数据**：多次保持间隔的测试成绩。
- **User State**：`forgetting_curve_params`。
- **定位**：Statistical Model。
- **优先级**：★★★★。

### [13] Averell & Heathcote (2011) — 遗忘曲线形式与记忆命运
- **研究问题**：遗忘曲线的最佳函数形式，以及记忆是整体衰减还是"部分记忆保留"。
- **核心理论**：指数 vs 幂律 vs 指数幂（exponential-power）。
- **IV**：保持间隔。
- **DV**：回忆概率分布。
- **主要结论**：exponential-power 拟合最佳；存在"永远记得"的稳定成分，并非全部衰减。
- **证据强度**：强（多种模型比较）。
- **局限**：实验室材料；模型依赖。
- **与本项目关系**：说明用户部分知识会长期稳定，Scheduler 应允许"毕业/长期不复习"。
- **系统设计**：加入 `mastered` 状态与长间隔抽查，而非无限重复。
- **可采集数据**：长间隔后的保持情况。
- **User State**：`stable_memory_fraction`、`mastered_flag`。
- **定位**：Statistical Model + Rule（毕业阈值）。
- **优先级**：★★★★。

### [14] Kornell (2009) — 卡片学习中的间隔 vs 突击
- **研究问题**：真实卡片学习中，间隔与突击的效果及学习者偏好。
- **核心理论**：间隔效应、元认知偏差。
- **IV**：间隔策略（间隔/突击/混合）。
- **DV**：延迟回忆。
- **主要结论**：间隔显著优于突击；学习者常误判突击更有效。
- **证据强度**：中—强（实验，生态化卡片任务）。
- **局限**：小样本、词表任务。
- **与本项目关系**：用户可能抵制分散安排，需要系统"强制+解释"。
- **系统设计**：用默认调度分散复习，并提供效果可视化以降低抵触。
- **可采集数据**：用户手动调整行为、复习分布。
- **User State**：`schedule_compliance`、`preference_bias`。
- **定位**：Rule（默认分散）+ LLM Harness（解释）。
- **优先级**：★★★★。

### [15] Bahrick & Phelps (1987) — 西班牙语词汇 8 年保持
- **研究问题**：真实二语词汇在数年至 8 年尺度上的保持与复习再学习效果。
- **核心理论**：长时程保持、再学习节省。
- **IV**：初始学习程度、复习次数、保持间隔（至 8 年）。
- **DV**：词汇回忆/再认。
- **主要结论**：保持先陡降后趋平；早期过度学习与后续复习显著提升长期保持。
- **证据强度**：中—强（纵向自然实验，样本可观）。
- **局限**：无严格随机；回忆指标依赖自评。
- **与本项目关系**：支持长周期（月/年）复习计划与"保持平台期"。
- **系统设计**：为长期目标设置稀疏但持续的复习点。
- **可采集数据**：长期间隔后的成绩、再学习时间。
- **User State**：`long_term_retention`、`relearning_savings`。
- **定位**：Statistical Model。
- **优先级**：★★★★。

### [16] Unsworth (2019) — 长时记忆个体差异综述
- **研究问题**：长时记忆（LTM）能力的个体差异结构及其与其他认知能力的关系。
- **核心理论**：LTM 能力因子结构；与工作记忆、智力、注意控制相关。
- **IV**：个体差异（任务类型：自由回忆/配对联想/再认等）。
- **DV**：LTM 各任务成绩；遗忘、干扰控制、错误记忆、测试效应、策略使用。
- **主要结论**：LTM 存在稳健的多层因子结构（含一般 LTM 因子与"遗忘"相关差异）；与 WMC/智力显著相关。
- **证据强度**：强（系统性综述，覆盖大量相关研究）。
- **局限**：相关设计为主，因果有限；多数为实验室任务。
- **与本项目关系**：证明"遗忘速度"确实存在稳定个体差异，支持 per-user 参数。
- **系统设计**：User Model 维护个性化的学习速率/遗忘率潜变量，而非全局常数。
- **可采集数据**：多任务表现、复习历史、策略自报。
- **User State**：`ltm_ability`、`forgetting_trait`、`wmc_proxy`。
- **定位**：ML（个体差异建模）+ Statistical Model。
- **优先级**：★★★★★。

### [17] Murre & Chessa (2011) — 幂律源于个体差异
- **研究问题**：学习/遗忘的"幂律"是否只是不同个体指数速率的平均假象？
- **核心理论**：指数函数的异质混合 → 幂律；速率服从 gamma/均匀/半正态分布。
- **IV**：学习/遗忘速率的个体分布。
- **DV**：平均学习/遗忘曲线形态。
- **主要结论**：数学证明平均化会产生幂律；个体层面可能是指数衰减；幂律参数不应直接当个体参数。
- **证据强度**：强（数学证明+模拟）。
- **局限**：理论/模拟，无实证拟合验证。
- **与本项目关系**：**关键**——不要用群体拟合的幂律参数套到个体；必须分层建模。
- **系统设计**：采用层级贝叶斯/混合模型，个体参数从个人数据估计。
- **可采集数据**：个体重复测量序列。
- **User State**：`individual_decay_rate`（个体后验）。
- **定位**：Statistical Model（层级模型）。
- **优先级**：★★★★★（建模方法学警钟）。

### [18] Xu et al. (2025) — DMN 连通性预测遗忘速度 ⚠️ 需 fMRI
- **研究问题**：静息态功能连接能否预测个体长时遗忘速度？
- **核心理论**：遗忘的"存储退化" vs "提取失败"假说；默认网络（DMN）维持记忆。
- **IV**：静息态 fMRI 连接模式。
- **DV**：由自适应配对联想任务估计的个体遗忘速度。
- **主要结论**：DMN（及其与感觉皮层）连接可高精度预测遗忘速度（r≈.77）；支持存储退化假说。
- **证据强度**：中—强（N=33，交叉验证；但样本小）。
- **局限**：**依赖 fMRI**，不可产品化；样本小；相关非因果。
- **与本项目关系**：提供"遗忘速度可估"的机制证据，但本项目应用行为数据替代神经数据。
- **系统设计**：不采集 fMRI；用自适应配对联想任务的行为表现作为遗忘速度代理。
- **可采集数据**：配对联想任务正确率+反应时（用于计算遗忘速度）。
- **User State**：`estimated_forgetting_speed`（行为代理）。
- **定位**：Statistical Model（估计器），神经部分仅作理论参考。
- **优先级**：★★★（理论价值高，落地受限）。

### [19] Lindsey et al. (2014) — 个性化复习提升保持
- **研究问题**：基于记忆模型的个性化复习排程能否提升学期末保持？
- **核心理论**：ACT-R/记忆强度模型驱动的个性化间隔。
- **IV**：排程策略（个性化模型 vs 等间隔/集中）。
- **DV**：学期内及期末测验成绩。
- **主要结论**：个性化复习在学期末显著提升保持，且可在较少复习量下达到同等成绩。
- **证据强度**：强（真实课堂准实验/实验，生态效度高）。
- **局限**：单一学科；模型假设固定。
- **与本项目关系**：Review Scheduler 的"个性化排程优于固定间隔"直接先例。
- **系统设计**：Scheduler 用动态记忆模型对每个知识点预测保持概率并排优先级。
- **可采集数据**：每次练习的对错、时间、知识点标签。
- **User State**：`per_item_memory_strength`。
- **定位**：Statistical Model + ML。
- **优先级**：★★★★★。

### [20] Settles & Meeder (2016) — 可训练间隔重复模型（半衰期回归）
- **研究问题**：用机器学习从大规模学习日志预测记忆半衰期，从而个性化复习。
- **核心理论**：half-life regression（HLR）；记忆半衰期随练习次数增长、随时间衰减。
- **IV**：用户特征、词汇难度、练习历史特征。
- **DV**：回忆概率（p(recall)）。
- **主要结论**：HLR 显著优于 Leitner/SM-2 等启发式，提升预测与学习效果（Duolingo 亿级日志）。
- **证据强度**：强（大规模真实数据+在线评估）；但为观察性/工程评估。
- **局限**：企业数据不可复现；语言学习单一场景。
- **与本项目关系**：可直接迁移的"半衰期回归"统计模型与特征设计。
- **系统设计**：Duration/Retention Predictor 采用 HLR 类模型；特征含历史表现与任务难度。
- **可采集数据**：复习日志、响应时、正确率、任务难度标签。
- **User State**：`half_life`、`recall_probability`。
- **定位**：Statistical Model → ML。
- **优先级**：★★★★★（工程最可直接复用）。

### [21] Reddy et al. (2016) — 无界人类学习的最优调度
- **研究问题**：在无限时间线上，如何最优安排复习以最大化记忆且控制复习成本？
- **核心理论**：随机最优控制；记忆状态转移。
- **IV**：调度策略/策略参数、成本权重。
- **DV**：长期回忆量与复习成本。
- **主要结论**：给出可证明近似最优的策略；优于固定间隔启发式。
- **证据强度**：中—强（理论保证+模拟/数据）。
- **局限**：模型简化；真实噪声未完全覆盖。
- **与本项目关系**：为 Review Scheduler 提供"成本—保持"权衡的形式化。
- **系统设计**：目标函数 `max Σrecall - λ·review_cost`，支持用户设置复习预算。
- **可采集数据**：复习成本（时长）、保持结果。
- **User State**：`review_budget`、`review_cost_sensitivity`。
- **定位**：Statistical Model / 优化器。
- **优先级**：★★★★。

### [22] Tabibian et al. (2019) — 基于点过程的间隔重复优化（MEMORIZE）
- **研究问题**：把间隔重复形式化为带跳随机微分方程的最优控制，求最优复习时刻。
- **核心理论**：标记时间点过程；最优复习时刻由"回忆概率本身"给出。
- **IV**：复习策略（MEMORIZE vs SM-2/Leitner 等）。
- **DV**：回忆概率、复习频率成本。
- **主要结论**：最优策略是"当回忆概率降到阈值时复习"；Duolingo 自然实验中优于多种启发式。
- **证据强度**：强（PNAS；理论+大规模自然实验）。
- **局限**：自然实验非随机；依赖记忆模型假设。
- **与本项目关系**：给出简洁、可实现的调度律（阈值触发复习）。
- **系统设计**：Scheduler 触发条件 = `recall_prob < θ`（θ 可个性化）。
- **可采集数据**：预测回忆概率、实际正确率、触发时点。
- **User State**：`recall_threshold`、`recall_prob_est`。
- **定位**：Rule + Statistical Model。
- **优先级**：★★★★★。

### [23] Zaidi et al. (2020) — 自适应遗忘曲线
- **研究问题**：能否为每个学习者学习自适应的遗忘曲线参数，以改善间隔重复？
- **核心理论**：个体化遗忘曲线；参数由数据拟合。
- **IV**：学习者、复习历史。
- **DV**：回忆预测精度/学习效果。
- **主要结论**：自适应遗忘曲线优于固定曲线，能捕捉个体差异。
- **证据强度**：中（AIED 会议论文，模型评估为主）。
- **局限**：会议论文，样本/复现有限。
- **与本项目关系**：支持 per-user 遗忘参数（与 [16][17] 呼应）。
- **系统设计**：User Model Update 周期性地为每个用户重估遗忘参数。
- **可采集数据**：复习日志序列。
- **User State**：`adaptive_forgetting_params`。
- **定位**：Statistical Model / ML。
- **优先级**：★★★★。

### [24] Xiao & Wang (2024) — DRL-SRS 深度强化学习调度
- **研究问题**：用深度强化学习优化间隔重复调度策略。
- **核心理论**：强化学习（状态=记忆状态，动作=复习/不复习，奖励=保持）。
- **IV**：调度算法（DRL vs SM-2/HLR）。
- **DV**：记忆保持率、复习次数。
- **主要结论**：DRL 调度在评测中优于传统启发式。
- **证据强度**：中（期刊应用研究，仿真/数据集评估）。
- **局限**：离线仿真与真实用户差距；可解释性弱。
- **与本项目关系**：Review Scheduler 可选的进阶 ML 方案（先行为模型，后 RL）。
- **系统设计**：作为 A/B 候选策略，与 HLR/阈值法对比。
- **可采集数据**：策略日志、奖励（成绩）。
- **User State**：`policy_version`。
- **定位**：ML（进阶）。
- **优先级**：★★★（先规则/统计，后 RL）。

### [25] Pokrywka et al. (2023) — LSTM 建模间隔重复
- **研究问题**：用 LSTM 序列模型预测复习后的回忆，替代手工记忆模型。
- **核心理论**：序列深度学习建模学习轨迹。
- **IV**：复习历史序列特征。
- **DV**：下次回忆正确率。
- **主要结论**：LSTM 可有效预测复习结果，具个性化潜力。
- **证据强度**：中（会议论文，离线评测）。
- **局限**：数据/可复现性有限；黑箱。
- **与本项目关系**：User Model 的序列建模备选。
- **系统设计**：当行为日志足够时，用序列模型增强 HLR。
- **可采集数据**：事件序列（时间、正误、题型）。
- **User State**：`sequence_embedding`。
- **定位**：ML。
- **优先级**：★★★。

### [26] Reddy et al. (2016, L@S) — 排队网络模型
- **研究问题**：把间隔重复视为排队系统，分析吞吐与学习产出。
- **核心理论**：排队网络 / 负载与遗忘的耦合。
- **IV**：队列调度规则、到达率。
- **DV**：系统吞吐、保持。
- **主要结论**：提供理解复习任务积压与遗忘竞争的分析框架。
- **证据强度**：中（理论建模）。
- **局限**：抽象假设强；实证少。
- **与本项目关系**：解释"复习任务积压"如何导致遗忘（Review backlog）。
- **系统设计**：Scheduler 需监控 review backlog 并设上限，避免任务雪崩。
- **可采集数据**：待复习队列长度、延迟复习时长。
- **User State**：`review_backlog`。
- **定位**：Rule（积压阈值）。
- **优先级**：★★★。

### [27] Xie et al. (2019) — 自适应/个性化学习系统综述
- **研究问题**：2007–2017 年技术增强自适应/个性化学习研究的趋势与方法。
- **核心理论**：自适应学习、个性化推荐、学习者建模。
- **IV**：系统类型、技术、学科、样本。
- **DV**：研究趋势/成效（综述层面）。
- **主要结论**：该领域快速增长；常用学习者特征（偏好、成绩、行为）；多基于规则/推荐，缺乏长期闭环评估。
- **证据强度**：中（系统综述，非效应量）。
- **局限**：仅期刊论文；未评估效果量。
- **与本项目关系**：定位本项目在自适应学习系统中的坐标与空白（长期闭环）。
- **系统设计**：明确用户模型维度与自适应触发点。
- **可采集数据**：文献/系统层面的设计要素（用于设计对照）。
- **User State**：`learner_profile`（多维）。
- **定位**：设计参考。
- **优先级**：★★★★（定位与综述）。

### [28] Kulik & Fletcher (2016) — 智能导师系统元分析
- **研究问题**：智能导师系统（ITS）相对传统教学的效果。
- **核心理论**：个别化辅导、掌握学习。
- **IV**：ITS vs 传统教学；学科/学段。
- **DV**：学业成就。
- **主要结论**：ITS 显著提升成绩（约 0.66 SD 量级）；效应受实施方式调节。
- **证据强度**：强（元分析）。
- **局限**：研究异质；多为短期。
- **与本项目关系**：证明"自动个别化辅导"有效，支持本系统的自适应规划价值。
- **系统设计**：任务难度与节奏个别化，而非统一计划。
- **可采集数据**：前后测成绩。
- **User State**：`mastery_level`。
- **定位**：Rule + ML。
- **优先级**：★★★★。

### [29] Ma et al. (2014) — ITS 与学习结果元分析
- **研究问题**：ITS 对学习结果的总体效应及调节变量。
- **核心理论**：智能辅导、反馈与脚手架。
- **IV**：ITS 类型、学科、时长、对照条件。
- **DV**：认知/情感结果。
- **主要结论**：ITS 对学习结果有中等偏上正效应（g≈0.6）；时长与学科调节。
- **证据强度**：强（元分析）。
- **局限**：发表偏倚；调节变量相关。
- **与本项目关系**：量化自适应辅导的期望收益。
- **系统设计**：以学习结果为主要评估指标。
- **可采集数据**：成绩、参与度。
- **User State**：`outcome_gain`。
- **定位**：评估基准。
- **优先级**：★★★☆。

### [30] VanLehn (2011) — 人类辅导 vs ITS 相对效力
- **研究问题**：人类辅导、ITS 与其他教学系统的相对效力。
- **核心理论**：辅导的"step-based"机制；交互粒度决定效果。
- **IV**：辅导类型/交互粒度（answer-based/step-based/substep）。
- **DV**：学习增益（效应量）。
- **主要结论**：step-based ITS 接近人类辅导效果；交互粒度而非"人类在场"是关键。
- **证据强度**：强（大规模效应量综述）。
- **局限**：以数学/物理为主；效应量估计依赖纳入标准。
- **与本项目关系**：说明细粒度任务分解+即时反馈是效果关键，指导计划粒度设计。
- **系统设计**：任务拆到 step 级，每次执行给反馈。
- **可采集数据**：步骤级完成/错误。
- **User State**：`step_granularity`、`hint_dependency`。
- **定位**：Rule + LLM Harness（分解任务）。
- **优先级**：★★★★。

### [31] Maye & Hurley (2026) — 医学教育中间隔重复元分析
- **研究问题**：间隔重复（如 Anki）在医学教育中对客观测试成绩的效果。
- **核心理论**：间隔重复、检索练习。
- **IV**：间隔重复使用 vs 对照；研究质量。
- **DV**：客观考试成绩。
- **主要结论**：间隔重复对考试成绩有正效应；纳入 14 项研究；总体证据质量中等。
- **证据强度**：中—强（系统综述+元分析，含 MERSQI 质量评估）。
- **局限**：医学教育场景；异质性与偏倚风险。
- **与本项目关系**：在职业教育/考试场景验证调度策略。
- **系统设计**：面向考试目标时启用密集间隔重复模式。
- **可采集数据**：考试成绩、Anki 使用日志。
- **User State**：`exam_readiness`。
- **定位**：Rule + Statistical Model。
- **优先级**：★★★★。

---

## 附：方向8 检索方法学备注
- API 调用均保存原始 JSON 于 `./api/`；`_verified_titles_*.json` 记录"候选题名→API 返回"的逐条核验，`_citation_meta.json` 记录 Crossref 返回的作者/卷期/页码/类型。
- 噪声控制：Europe PMC 的 `sort=CITED desc` 会混入全球高被引无关文献（如 MEGA7、FreeSurfer），已人工剔除；改用精确题名 `TITLE:"..."` 与 `AUTH:` 组合过滤。
- 未采纳但值得后续关注：`10.1016/j.lmot.2026.102310`（自适应间隔训练与工作记忆，2026, Learning and Motivation）。
