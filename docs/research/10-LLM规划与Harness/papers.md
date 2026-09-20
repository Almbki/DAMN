# 方向10：LLM 规划与 Harness / 可靠性 — 文献调研

> **检索 53 篇，采纳 31 篇（编号 1–31）。**
> 检索方式：全部条目均经 arXiv 官方 API（export.arxiv.org）实际抓取验证（53 条入口，其中 3 个凭记忆给出的错误 ID、1 处论文-ID 职责错位被 API 返回值当场纠正），并另用 Semantic Scholar API 批量核实 29 条元数据（venue/year）。所有链接均真实可访问。检索日期：2026-09-19。
> 每篇文献格式：GB/T 7714 引用 + 源链接 + 分析模板。

**四个重点子问题覆盖情况**：
- 子问题1（何时不调用 LLM：routing/cascade/adaptive invocation）：文献 1-7
- 子问题2（外部模型辅助 LLM：tool-augmented / verifier / structured context）：文献 8-15
- 子问题3（验证 LLM 生成的计划：verifier / critic / constrained generation / benchmark）：文献 16-25、26-27
- 子问题4（降低 LLM 调用成本 + Agent 评估）：文献 28-32，涉及 MoA / Preble / AgentBench / WebArena / GAIA

---

## 一、采纳文献清单（GB/T 7714）

### 子问题1：何时不调用 LLM（路由 / 级联 / 自适应调用）

[1] CHEN L, ZAHARIA M, ZOU J. FrugalGPT: How to use large language models while reducing cost and improving performance[J]. Transactions on Machine Learning Research, 2023.

[2] DING D, MALLICK A, WANG C, et al. Hybrid LLM: Cost-efficient and quality-aware query routing[C]//The Twelfth International Conference on Learning Representations (ICLR 2024). 2024.

[3] ONG I, ALMAHAIRI A, WU V, et al. RouteLLM: Learning to route LLMs with preference data[EB/OL]. arXiv:2406.18665, 2024.

[4] HU Q J, BIEKER J, LI X, et al. RouterBench: A benchmark for multi-LLM routing system[EB/OL]. arXiv:2403.12031, 2024.

[5] ZELLINGER M J, THOMSON M. Rational tuning of LLM cascades via probabilistic modeling[EB/OL]. arXiv:2501.09345, 2025.

[6] ZELLINGER M J, LIU R, THOMSON M. Cost-saving LLM cascades with early abstention[EB/OL]. arXiv:2502.09054, 2025.

[7] SRIVATSA V, HE Z, ABHYANKAR R, et al. Preble: Efficient distributed prompt scheduling for LLM serving[EB/OL]. arXiv:2407.00023, 2024.

### 子问题2：外部模型辅助 LLM（工具 / 验证器 / 结构化上下文）

[8] YAO S, ZHAO J, YU D, et al. ReAct: Synergizing reasoning and acting in language models[C]//The Eleventh International Conference on Learning Representations (ICLR 2023). 2023.

[9] SCHICK T, DWIVEDI-YU J, DESSÌ R, et al. Toolformer: Language models can teach themselves to use tools[C]//Advances in Neural Information Processing Systems 36 (NeurIPS 2023). 2023.

[10] PATIL S G, ZHANG T, WANG X, et al. Gorilla: Large language model connected with massive APIs[C]//Advances in Neural Information Processing Systems 36 (NeurIPS 2023). 2023.

[11] GOU Z, SHAO Z, GONG Y, et al. CRITIC: Large language models can self-correct with tool-interactive critiquing[C]//The Twelfth International Conference on Learning Representations (ICLR 2024). 2024.

[12] LIU B, JIANG Y, ZHANG X, et al. LLM+P: Empowering large language models with optimal planning proficiency[EB/OL]. arXiv:2304.11477, 2023.

[13] KAGAYA T, YUAN T J, LOU Y, et al. RAP: Retrieval-augmented planning with contextual memory for multimodal LLM agents[EB/OL]. arXiv:2402.03610, 2024.

[14] WANG G, XIE Y, JIANG Y, et al. Voyager: An open-ended embodied agent with large language models[J]. Transactions on Machine Learning Research, 2023.

[15] PACKER C, WOODERS S, LIN K, et al. MemGPT: Towards LLMs as operating systems[EB/OL]. arXiv:2310.08560, 2023.

### 子问题3：验证 LLM 生成的计划（验证器 / 批评者 / 约束生成 / 评测基准）

[16] LIGHTMAN H, KOSARAJU V, BURDA Y, et al. Let's verify step by step[C]//The Twelfth International Conference on Learning Representations (ICLR 2024). 2024.

[17] VALMEEKAM K, MARQUEZ M, OLMO A, et al. PlanBench: An extensible benchmark for evaluating large language models on planning and reasoning about change[C]//Advances in Neural Information Processing Systems 36 (NeurIPS 2023, Datasets and Benchmarks Track). 2023.

[18] VALMEEKAM K, STECHLY K, KAMBHAMPATI S. LLMs still can't plan; Can LRMs? A preliminary evaluation of OpenAI's o1 on PlanBench[EB/OL]. arXiv:2409.13373, 2024.

[19] KAMBHAMPATI S. Can large language models reason and plan?[J]. Annals of the New York Academy of Sciences, 2024. DOI: 10.1111/nyas.15125.

[20] KAMBHAMPATI S, VALMEEKAM K, GUAN L, et al. LLMs can't plan, but can help planning in LLM-Modulo frameworks[C]//Proceedings of the 41st International Conference on Machine Learning (ICML 2024). PMLR 235, 2024.

[21] MADAAN A, TANDON N, GUPTA P, et al. Self-Refine: Iterative refinement with self-feedback[C]//Advances in Neural Information Processing Systems 36 (NeurIPS 2023). 2023.

[22] SHINN N, CASSANO F, BERMAN E, et al. Reflexion: Language agents with verbal reinforcement learning[C]//Advances in Neural Information Processing Systems 36 (NeurIPS 2023). 2023.

[23] YAO S, YU D, ZHAO J, et al. Tree of Thoughts: Deliberate problem solving with large language models[C]//Advances in Neural Information Processing Systems 36 (NeurIPS 2023). 2023.

[24] SUN H, ZHUANG Y, KONG L, et al. AdaPlanner: Adaptive planning from feedback with language models[EB/OL]. arXiv:2305.16653, 2023.

[25] PARK K, ZHOU T, D'ANTONI L. Flexible and efficient grammar-constrained decoding[EB/OL]. arXiv:2502.05111, 2025.

[26] WEI J, WANG X, SCHUURMANS D, et al. Chain-of-thought prompting elicits reasoning in large language models[C]//Advances in Neural Information Processing Systems 35 (NeurIPS 2022). 2022.

[27] WANG X, WEI J, SCHUURMANS D, et al. Self-consistency improves chain of thought reasoning in language models[C]//The Eleventh International Conference on Learning Representations (ICLR 2023). 2023.

### 子问题4：降低 LLM 调用成本 + Agent 评测

[28] WANG J, WANG J, ATHIWARATKUN B, et al. Mixture-of-Agents enhances large language model capabilities[EB/OL]. arXiv:2406.04692, 2024.

[29] LIU X, YU H, ZHANG H, et al. AgentBench: Evaluating LLMs as agents[C]//The Twelfth International Conference on Learning Representations (ICLR 2024). 2024.

[30] ZHOU S, XU F F, ZHU H, et al. WebArena: A realistic web environment for building autonomous agents[C]//The Twelfth International Conference on Learning Representations (ICLR 2024). 2024.

[31] MIALON G, FOURRIER C, SWIFT C, et al. GAIA: A benchmark for general AI assistants[EB/OL]. arXiv:2311.12983, 2023.

> 说明：实际采纳 31 篇独立文献（编号 1–31），其中 [18] 为 [17]（PlanBench）的后续实证论文，一并采纳。

---

## 二、源链接（按上文编号）

1. https://arxiv.org/abs/2305.05176 （FrugalGPT）
2. https://arxiv.org/abs/2404.14618 （Hybrid LLM）
3. https://arxiv.org/abs/2406.18665 （RouteLLM）
4. https://arxiv.org/abs/2403.12031 （RouterBench）
5. https://arxiv.org/abs/2501.09345 （Rational Tuning of LLM Cascades）
6. https://arxiv.org/abs/2502.09054 （Cost-Saving LLM Cascades with Early Abstention）
7. https://arxiv.org/abs/2407.00023 （Preble）
8. https://arxiv.org/abs/2210.03629 （ReAct）
9. https://arxiv.org/abs/2302.04761 （Toolformer）
10. https://arxiv.org/abs/2305.15334 （Gorilla）
11. https://arxiv.org/abs/2305.11738 （CRITIC）
12. https://arxiv.org/abs/2304.11477 （LLM+P）
13. https://arxiv.org/abs/2402.03610 （RAP: Retrieval-Augmented Planning）
14. https://arxiv.org/abs/2305.16291 （Voyager）
15. https://arxiv.org/abs/2310.08560 （MemGPT）
16. https://arxiv.org/abs/2305.20050 （Let's Verify Step by Step）
17. https://arxiv.org/abs/2206.10498 （PlanBench）
18. https://arxiv.org/abs/2409.13373 （LLMs Still Can't Plan; Can LRMs?）
19. https://arxiv.org/abs/2403.04121 （Can Large Language Models Reason and Plan?；DOI: https://doi.org/10.1111/nyas.15125）
20. https://arxiv.org/abs/2402.01817 （LLM-Modulo Frameworks）
21. https://arxiv.org/abs/2303.17651 （Self-Refine）
22. https://arxiv.org/abs/2303.11366 （Reflexion）
23. https://arxiv.org/abs/2305.10601 （Tree of Thoughts）
24. https://arxiv.org/abs/2305.16653 （AdaPlanner）
25. https://arxiv.org/abs/2502.05111 （Grammar-Constrained Decoding）
26. https://arxiv.org/abs/2201.11903 （Chain-of-Thought Prompting）
27. https://arxiv.org/abs/2203.11171 （Self-Consistency）
28. https://arxiv.org/abs/2406.04692 （Mixture-of-Agents）
29. https://arxiv.org/abs/2308.03688 （AgentBench）
30. https://arxiv.org/abs/2307.13854 （WebArena）
31. https://arxiv.org/abs/2311.12983 （GAIA）

<!-- TEMPLATE_PART2 -->

---

## 三、逐篇分析模板

### [1] FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance（arXiv:2305.05176，TMLR 2023）

- **研究问题**：LLM API 调用费用高（不同模型差异可达两个数量级），如何系统性降低推理成本且不损失（甚至提升）效果？
- **核心理论**：提出三类成本降低策略——提示词适配（prompt adaptation）、LLM 近似（approximation）、LLM 级联（cascade）；FrugalGPT 是级联的实例化：为每次查询学习"选哪几个模型、按什么顺序调用、何时停止"。
- **IV**：LLM 组合与调用顺序、每级置信度阈值、查询特征。**DV**：回答准确率、推理成本（美元）、成本-准确率曲线下面积。
- **主要结论**：级联可用 **GPT-4 的 2% 成本**达到同等准确率；同成本下比 GPT-4 准确率再高 4%。模型间错误率相关性低、不同模型擅长的查询不同，使级联优于单模型。
- **证据强度**：强实证（多数据集、多模型 API、成本-质量权衡曲线），TMLR 发表。
- **研究局限**：依赖各模型 API 定价假设；阈值学习需要标注数据；未涉及交互式/多步 Agent 场景。
- **与本项目的关系**：本项目"简单变化走 Rule+Scheduler、重大变化才走 LLM"正是 lazily-invoked cascade 思路；FrugalGPT 提供了成本模型与级联停止规则的数学框架。
- **可支持的系统设计**：LLM 调用门控（Gate）——计划版本变化小时直接复用旧计划/规则重排，仅在 replan 时才级联到 LLM；可二次级联：小模型先出候选，规则校验不满意再升级大模型。
- **可采集的数据**：每次 LLM 调用的事件日志（节点名、模型、token 数、成本、是否通过 RuleEngine）、每类用户请求的通过/拒绝率。
- **可形成的 User State**：llm_reliance_score（用户请求历史中触发 LLM 的比例）、plan_stability（计划版本间平均差异大小）。
- **可作为系统的哪一部分**：Application 层的 LLM 成本/调度策略；Rule→LLM 触发阈值学习（Statistical Model）；成本核算模块。
- **推荐优先级及原因**：★★★★★。是第一篇系统化"能不调就不调"的论文，直接支撑本项目最核心的架构决策（Scheduler 不调用 LLM、replan 冷却期按用户）。

### [2] Hybrid LLM: Cost-Efficient and Quality-Aware Query Routing（arXiv:2404.14618，ICLR 2024）

- **研究问题**：如何在一个查询上动态决定用大模型还是小模型，达到"质量不降、成本大幅下降"？
- **核心理论**：用路由器（router）预测查询难度，按目标质量水平把查询分派给小/大模型；质量水平可在测试时动态调节，实现"质量-成本"连续折中。
- **IV**：查询嵌入特征、质量阈值（test-time 可调）、路由器类型。**DV**：大模型调用比例、响应质量（下游客任务指标）。
- **主要结论**：路由器可减少 **高达 40%** 的大模型调用且零质量损失；将质量阈值暴露给系统可动态权衡；小模型强于难度回归、大模型强于复杂任务时路由收益最大。
- **证据强度**：强实证，ICLR 主会发表，多个任务与模型规模配置。
- **研究局限**：质量评估依赖任务指标；路由器本身是额外开销；未覆盖约束/多步 Agent 内部路由。
- **与本项目的关系**：本项目 LLM 只负责 plan generation/replan 节点，其余节点是确定性模块——本质是"任务级路由"；Hybrid LLM 给出路由器的输入特征与可调质量门限设计。
- **可支持的系统设计**：PlanScorer 门限机制：只有当候选计划质量分（模型预测或启发式评分）低于阈值时才触发 LLM 重生成；质量-成本预算接口暴露给用户/运维。
- **可采集的数据**：历史查询特征（goal 文本、domain、时间）→ 是否真正需要 LLM 的标签；小模型 vs 大模型在各类计划任务上的命中率对比。
- **可形成的 User State**：query_difficulty（该用户目标的预测难度分）、plan_quality_needed（用户对计划精细度的偏好）。
- **可作为系统的哪一部分**：ML（路由分类器/回归器）；触发 replan 的置信度阈值 = Statistical Model 参数。
- **推荐优先级及原因**：★★★★☆。路由思想的工程化模板，适用于"何时该动用昂贵 LLM"的决策层。

### [3] RouteLLM: Learning to Route LLMs with Preference Data（arXiv:2406.18665）

- **研究问题**：如何用人类偏好数据训练路由器，在强/弱两个模型间动态选择，兼顾成本与质量？
- **核心理论**：把路由视为二分类"该用强模型吗"；用偏好数据（含强弱模型输出对比与"平局"标签）训练/提示路由器；提出 matrix factorization、BERT 分类器、因果 LM 提示、BGE 嵌入等路由模型。
- **IV**：路由器架构、训练数据规模与偏好增强策略。**DV**：路由成本削减比例、相对于强模型的质量保持率（win rate）。
- **主要结论**：在广泛基准上 **成本降低 2 倍以上**且质量不降；路由器在强/弱模型替换（test-time 换模型）时仍有良好迁移，说明学到的是任务难度信号而非具体模型。
- **证据强度**：强实证（大规模偏好数据、多基准、开源权重）；I CLR 2025 社区标准对比常用基线。
- **研究局限**：偏好数据标注成本；路由器表现依赖基准覆盖；静态推理（单次调用）假设。
- **与本项目的关系**："学习何时用大模型"与本项目 replan 触发条件学习同构；其迁移性结论支持"路由器只依赖任务特征而非模型品牌"。
- **可支持的系统设计**：为 plan_generation 节点配备基于任务特征（目标类型、上下文长度、历史失败率）的难度路由，难任务用大模型、易任务用小模型/规则。
- **可采集的数据**：同一 goal 下大/小模型生成计划 + RuleEngine 通过率 → 构建偏好对（通过的 > 失败的）。
- **可形成的 User State**：historical_plan_failure_rate、goal_domain_complexity。
- **可作为系统的哪一部分**：ML 路由层（ReplanGater）；偏好数据管道。
- **推荐优先级及原因**：★★★★。可落地的路由训练配方，且其"偏好对=通过/不通过"的构造与本项目 RuleEngine 校验结果天然契合。

### [4] RouterBench: A Benchmark for Multi-LLM Routing System（arXiv:2403.12031）

- **研究问题**：路由系统效果如何标准化评估？此前缺乏统一基准。
- **核心理论**：提出路由评估框架 + **405k 条推理结果数据集**，形式化"路由 = 组合多模型以最优化质量-成本"问题，并对比多种路由策略。
- **IV**：路由算法类型（单模型/级联/路由）。**DV**：质量（准确率）、成本、成本-质量曲线。
- **主要结论**：没有单一模型全能；级联与路由在成本-质量平面上优势明显；不同策略的可路由增益（routability gain）差异显著。
- **证据强度**：基准论文（405k 推理结果实证数据）。
- **研究局限**：覆盖模型/任务集合固定；推理结果集存在分布漂移问题。
- **与本项目的关系**：为"何时用哪个模型"提供评估方法论，可迁移为本项目 LLM 使用策略的离线评估框架。
- **可支持的系统设计**：建立本项目自身的小型路由评估集：历史 goal→plan→RuleEngine 结果构成 mini-RouterBench，离线选择 replan 触发规则。
- **可采集的数据**：各 LLM 节点输出的质量分数矩阵（goal × model × 通过率）、成本矩阵。
- **可形成的 User State**：不直接形成，但可支撑 model_effectiveness_profile。
- **可作为系统的哪一部分**：评估/评测层（离线对比不同 harness 策略）。
- **推荐优先级及原因**：★★★☆。用于项目"路由决策是否划算"的离线验证，不直接进运行时。

### [5] Rational Tuning of LLM Cascades via Probabilistic Modeling（arXiv:2501.09345）

- **研究问题**：级联系统的每级置信度阈值在数据少时如何理性调优？各模型错误率如何交互？
- **核心理论**：用参数化 **Markov-copula 模型** 建模级联中多个 LLM 的联合错误分布（捕捉模型间错误相关性），把阈值调优变为连续优化问题。
- **IV**：级联长度 k、训练样本量 n、阈值组合。**DV**：error-cost 权衡曲线下面积、样本效率。
- **主要结论**：相比贝叶斯优化选阈值，Markov-copula 使误差-成本曲线面积平均改善 **4.3%**（k≥3 级联），低样本（n≤30）时改善达 **10.2%**——合理归纳偏差（错误相关性）带来样本效率。
- **证据强度**：中等偏强；系统性消融（多级联长度、少样本情境模拟）。
- **研究局限**：copula 参数假设较强；实验基于代理指标而非端到端真实成本。
- **与本项目的关系**：本项目多级管线（LLM 生成 → RuleEngine → 成功率反馈）可视为级联；"错误相关性建模"提示 LLM 输出与规则放行之间不是独立事件，调优 replan 阈值时应联合建模。
- **可支持的系统设计**：replan 阈值随用户历史成功率的自适应校准；用户数少（n≤30）时用先验模型冷启动阈值。
- **可采集的数据**：每用户 replan 历史（触发→执行→通过率）、计划被 RuleEngine 拒绝率。
- **可形成的 User State**：user_replan_threshold_prior（冷启动默认阈值）、user_error_correlation。
- **可作为系统的哪一部分**：Statistical Model（replan 阈值校准）；LLM Harness 的级联控制器。
- **推荐优先级及原因**：★★★★。给出"小样本下调阈值"的数学方法，正好应对本项目用户冷启动问题。

### [6] Cost-Saving LLM Cascades with Early Abstention（arXiv:2502.09054）

- **研究问题**：高风险场景中，级联系统是否应在早期模型就"拒绝回答"，避免把必错问题送进昂贵大模型？
- **核心理论**：在级联各层（不只最后一层）引入 abstention（放弃作答）选项；利用小/大模型错误模式的相关性，提前放弃相关度高的难查询。
- **IV**：是否允许 early abstention、abstention 阈值、级联层数。**DV**：测试损失、abstention 率、推理成本、错误率。
- **主要结论**：early abstention 在 6 个基准（GSM8K/MedMCQA/MMLU/TriviaQA/TruthfulQA/XSum）平均降低测试损失 **2.2%**；以 abstention 率 +4.1% 换取成本 -13%、错误率 -5.0%。
- **证据强度**：中等偏强（6 基准实证）。
- **研究局限**：abstention 需要下游可处理"无计划"；侧重单轮问答而非多步规划。
- **与本项目的关系**：直接支持"计划不可行时宁可拒绝生成，也不要硬编"；RuleEngine 拒绝即 abstention，可前置到 LLM 调用前（用规则/预测器判断该目标是否根本不可规划）。
- **可支持的系统设计**：计划可行性预检（Preflight Check）：goal 明显不可执行（无时间/无前置条件）时直接返回"无法规划"而非调 LLM；执行反馈连续失败时提前退出 replan 循环。
- **可采集的数据**：RuleEngine 拒绝原因分布、早期失败信号（未开始即失败的任务）→ 训练 abstention 分类器。
- **可形成的 User State**：goal_feasibility_probability（该类型目标的历史可行性）。
- **可作为系统的哪一部分**：Rule 层（可行性硬规则）+ ML 层（可行性分类器）→ LLM Harness 的前置门控。
- **推荐优先级及原因**：★★★★。本项目"RuleEngine 是唯一硬约束权威"与此论文的 abstention 设计完全同构。

### [7] Preble: Efficient Distributed Prompt Scheduling for LLM Serving（arXiv:2407.00023）

- **研究问题**：生产级 LLM 服务中，跨请求共享的 prompt 前缀（系统提示、工具说明、长上下文）如何调度以复用 KV 缓存、降低算力成本？
- **核心理论**：首个面向 prompt 共享的分布式调度系统：调度算法协同优化 KV 状态复用与计算负载均衡，层级调度机制管理跨机缓存。
- **IV**：调度算法、层级数、工作负载到达模式。**DV**：平均延迟、p99 延迟、吞吐。
- **主要结论**：相比 SOTA 服务系统，平均延迟提升 **1.5×–14.5×**，p99 延迟提升 **2×–10×**。
- **证据强度**：强系统实证（真实工作负载、两个开源 LLM）。
- **研究局限**：面向自托管服务；不解决"该不该调 LLM"本身。
- **与本项目的关系**：本项目 prompt 中固定注入 User State、RuleEngine 规则摘要等结构化上下文——这些前缀高度可缓存；多用户共享模板 → KV 复用潜力大。
- **可支持的系统设计**：把用户无关的系统提示（规则 schema、输出格式）与用户相关上下文分层组织，为 prefix-caching 做准备；LangGraph 各节点共用同一系统提示模板。
- **可采集的数据**：prompt 前缀重复率、每节点输入/输出 token 分布、缓存命中率。
- **可形成的 User State**：无直接关系，但 llm_context_size 影响成本估算。
- **可作为系统的哪一部分**：基础设施层（成本优化，非运行时逻辑）。
- **推荐优先级及原因**：★★★。属于成本工程而非 Agent 语义，但为"减少 LLM 调用成本"子问题提供系统侧证据。

### [8] ReAct: Synergizing Reasoning and Acting in Language Models（arXiv:2210.03629，ICLR 2023）

- **研究问题**：让 LLM 交替"推理轨迹"与"行动"（调用外部工具/环境交互）能否同时改善推理可靠性（防幻觉）与决策效果？
- **核心理论**：ReAct——推理（thought）与行动（act）交错生成，行动结果作为观察（observation）喂回模型；外部 API 作为事实来源。
- **IV**：是否启用推理+行动、工具可用性（Wikipedia API 等）、示例数量。**DV**：问答/事实验证准确率、交互决策成功率（ALFWorld/WebShop）、可解释性。
- **主要结论**：在 HotpotQA/Fever 上克服 CoT 的幻觉与错误传播；ALFWorld/WebShop 上绝对成功率分别超模仿学习与强化学习基线 **34%/10%**，仅需 1-2 个 in-context 示例。
- **证据强度**：强实证（4 个任务族、多 LLM 规模），ICLR 2023 主会。
- **研究局限**：依赖可用工具；轨迹长、token 消耗大；工具错误会传播。
- **与本项目的关系**：本项目 LangGraph 节点即"think（plan candidates）→ act（RuleEngine/Scheduler）→ observe（feedback）"，ReAct 是此架构的直接理论祖先；其"外部接口减少幻觉"机制验证了 RuleEngine 作为外部事实源的价值。
- **可支持的系统设计**：在 plan 生成节点 prompt 中要求 LLM 先输出"约束检查 thought"再输出结构化候选；执行反馈作为 observation 重新注入 replan。
- **可采集的数据**：thought/act 轨迹、工具调用结果、每步修正量——用于训练"何时走 LLM vs 规则"的分类器。
- **可形成的 User State**：tool_reliability_history（每次执行反馈的置信度）、task_interaction_depth。
- **可作为系统的哪一部分**：LangGraph 图结构的理论模板；LLM Harness 的观察反馈回路。
- **推荐优先级及原因**：★★★★★。本项目闭环（生成→校验→执行→反馈→replan）几乎就是 ReAct 在任务规划领域的实例化。

### [9] Toolformer: Language Models Can Teach Themselves to Use Tools（arXiv:2302.04761，NeurIPS 2023）

- **研究问题**：LLM 如何自主学习"何时调用外部工具（计算器、搜索引擎、日历等）、调哪个、传什么参数"？
- **核心理论**：自监督工具学习——在语料中标注"插入 API 调用"的位置，用"调用后预测损失是否下降"的自我审核决定保留/丢弃，微调模型学会调用工具。
- **IV**：工具类型、自监督数据量、模型规模。**DV**：下游任务零样本性能、困惑度保持。
- **主要结论**：Toolformer 在算术/QA 等任务上零样本性能大幅提升，可与远超自身规模的模型竞争，且不牺牲语言建模能力——"工具调用让简单能力（算术）不再依赖模型规模"。
- **证据强度**：强实证（多任务、去工具消融后性能回落）。
- **研究局限**：工具调用是隐式学习，可解释性弱；每 API 需少量演示；推理时工具选择不可控。
- **与本项目的关系**："外部工具完成 LLM 不擅长的确定性计算"——本项目 Duration Predictor、Scheduler 正是这类工具；Toolformer 论证了"LLM 与工具分工"的正交性。
- **可支持的系统设计**：为 plan 生成节点注入"工具清单"（Duration Predictor / 规则查询 / 统计模型），要求 LLM 显式声明使用哪个工具的结果作为依据（tool grounding 标记）。
- **可采集的数据**：LLM 生成的 tool-use 声明及其与实际调用的一致性 → 检验 LLM 是否诚实使用工具。
- **可形成的 User State**：tool_grounding_reliability（该用户目标类别中 LLM 工具引用正确率）。
- **可作为系统的哪一部分**：LLM Harness 的 tool-use 协议（结构化 context 里的工具 schema）。
- **推荐优先级及原因**：★★★☆。思想直接相关，但自监督微调范式与本项目"无训练、prompt 化"路线不同，作为设计参考。

### [10] Gorilla: Large Language Model Connected with Massive APIs（arXiv:2305.15334，NeurIPS 2023）

- **研究问题**：LLM 在 API 调用上幻觉严重（参数错误、虚构 API），如何让它可靠调用大量 API？
- **核心理论**：微调生成 API 调用（APIBench 数据集），并配合**文档检索器**在测试时注入最新 API 文档（retrieval-aware）——不依赖训练时看到的文档。
- **IV**：微调 vs 黑盒提示、是否接文档检索器、文档版本变化。**DV**：API 调用准确率、幻觉（虚构 API）率、对文档变更的适应能力。
- **主要结论**：Gorilla 在写 API 调用上超过 GPT-4；接检索器后显著缓解幻觉（不虚构不存在 API），并适应 test-time 文档更新。
- **证据强度**：强实证（APIBench：HuggingFace/TorchHub/TensorHub 大规模数据集）。
- **研究局限**：API 域限定；需要微调；单步 API 调用而非多步。
- **与本项目的关系**：本项目 LLM 不碰 DB，但会"调用"User State/预测器/规则摘要——Gorilla 证明"给模型注入动态结构化上下文（retrieved schema）比让模型记忆更可靠"。
- **可支持的系统设计**：plan 生成节点的 prompt 中动态注入用户/领域相关的工具与 Schema（可用时间段窗口、规则列表），类似 retrieval-augmented tool doc。
- **可采集的数据**：LLM 输出中引用不存在的"能力/字段"的比例（幻觉度量）；注入文档版本与输出质量的关联。
- **可形成的 User State**：schema_adherence_rate（用户计划中引用合法字段的比例）。
- **可作为系统的哪一部分**：LLM Harness 的工具文档检索（structured context 来源）。
- **推荐优先级及原因**：★★★★。为"结构化上下文注入"提供检索增强的工程模式，其幻觉度量方法可复用于本项目 LLM 输出审计。

### [11] CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing（arXiv:2305.11738，ICLR 2024）

- **研究问题**：LLM 自我纠错常常空转（自我批评无外部依据），让模型借助外部工具做"可验证的批评"能否真正提高输出可靠性？
- **核心理论**：CRITIC 循环——初始输出 → 用合适工具（搜索、解释器等）逐项验证（critique）→ 依据工具反馈修订 → 迭代。外部工具提供事实性验证信号。
- **IV**：验证工具可用性、迭代轮数、任务类型。**DV**：事实正确率、代码正确率、毒性分数等任务指标。
- **主要结论**：在自由问答、数学程序合成、毒性降低三域一致提升；**外部验证反馈是自我提升的关键**（纯自我批评收益有限）。
- **证据强度**：强实证（三任务族、多模型、多轮消融）。
- **研究局限**：依赖工具覆盖验证范围；多轮迭代成本线性增加。
- **与本项目的关系**：本项目"执行反馈 → replan"即工具交互式批评；可进一步在生成阶段用 RuleEngine 干跑校验作为"工具验证"，比 prompt 自检可靠。
- **可支持的系统设计**：rule_validation 节点从"事后拦截"升级为"批评循环"：RuleEngine 拒绝时把违规项作为结构化批评喂回 LLM 修订（而非直接放弃），限定最多 1-2 轮以控成本。
- **可采集的数据**：RuleEngine 拒绝类别 × 修订后通过率（验证批评信号的有效性）；每目标平均修订轮数。
- **可形成的 User State**：revision_effectiveness（该用户目标下修订成功的概率）。
- **可作为系统的哪一部分**：LLM Harness 的 verifier-feedback 回路 + Rule 层的错误类别字典。
- **推荐优先级及原因**：★★★★★。证明"外部验证 > 内部自省"，正是本项目 RuleEngine 权威性的理论支撑。

### [12] LLM+P: Empowering Large Language Models with Optimal Planning Proficiency（arXiv:2304.11477）

- **研究问题**：长 horizon 规划任务 LLM 不可靠，能否让 LLM 只做"翻译员"，把问题转成 PDDL 交给经典规划器求解？
- **核心理论**：LLM 将自然语言问题 → PDDL 域/问题文件 → 经典规划器求最优解 → LLM 把解转回自然语言。
- **IV**：规划框架（LLM+P vs 直接 LLM 提示）。**DV**：规划可行性（是否满足目标）、最优性。
- **主要结论**：LLM+P 对多数基准问题给出最优解；直接提示 LLM 对多数问题连可行方案都给不出。
- **证据强度**：强实证（多个 IPC 风格规划域基准），但有后续批评称所用问题难度偏低。
- **研究局限**：PDDL 翻译本身会出错；问题必须可形式化；对开放领域、非经典规划不适配。
- **与本项目的关系**：本项目 RuleEngine + Scheduler 即"符号规划器"角色；LLM 生成候选 → 硬规则校验即"LLM+外部求解器"混合，支持"LLM 负责松约束生成、精确求解交给确定性模块"。
- **可支持的系统设计**：当目标可形式化（依赖关系、时限、优先级明确）时跳过 LLM，用确定性算法（拓扑排序 + 规则 + 调度器）生成计划；LLM 仅处理模糊目标。
- **可采集的数据**：目标可形式化程度评分 → 实际 LLM 使用/计划质量对比（验证"哪些目标不值得调 LLM"）。
- **可形成的 User State**：goal_formalizability（该用户目标被规则完整覆盖的比例）。
- **可作为系统的哪一部分**：路由决策特征 + Scheduler 确定性计划器升级路径。
- **推荐优先级及原因**：★★★★。最直接支撑"能用确定性方法就别用 LLM"的本项目核心设计。

### [13] RAP: Retrieval-Augmented Planning with Contextual Memory for Multimodal LLM Agents（arXiv:2402.03610）

- **研究问题**：Agent 如何从过去经验中检索"与当前情景相似的情境"来辅助当前规划？
- **核心理论**：把历史经验按情景上下文存为记忆，规划时检索相似经验（similarity-based retrieval）注入 prompt；文本与多模态环境通用。
- **IV**：是否使用检索记忆、记忆粒度、相似度度量。**DV**：文本/多模态环境的任务成功率、SOTA 对比。
- **主要结论**：文本场景达 SOTA；多模态具身任务显著提升；验证"检索到的过往经验 > 冷启动规划"。
- **证据强度**：中等偏强（多任务实证）——于 arXiv 发布（S2 无会议记录）。
- **研究局限**：检索质量依赖嵌入模型；记忆随规模增大的存储成本。
- **与本项目的关系**：本项目 replan 基于用户执行历史——RAP 提供形式化：把"历史计划+反馈"存为可检索经验库，同类目标直接复用成功模式。
- **可支持的系统设计**：Plan Memory 库：goal 特征嵌入 → 检索历史成功计划模板/失败原因，作为 LLM 的 few-shot 上下文；与 ReplanEvent 数据打通。
- **可采集的数据**：目标 → 历史计划的成功/失败标签、最优检索 k 值、记忆命中率与计划质量提升幅度。
- **可形成的 User State**：plan_style_similarity（当前目标与用户历史成功目标的重合度）。
- **可作为系统的哪一部分**：LLM Harness 的 few-shot 检索注入 + ML（嵌入检索）层。
- **推荐优先级及原因**：★★★★。把执行反馈沉淀为可复用记忆，直接提升 replan 质量并降低重复 LLM 调用（相似目标免 LLM）。

### [14] Voyager: An Open-Ended Embodied Agent with Large Language Models（arXiv:2305.16291，TMLR 2023）

- **研究问题**：长期终身学习 Agent 如何持续积累可复用技能、防止灾难性遗忘、自动验证自身成果？
- **核心理论**：三组件——自动课程（按当前能力指派任务）、**可增长技能库**（代码化技能，检索复用）、迭代式 prompt 机制（环境反馈+执行错误+**自我验证**驱动程序改进）。
- **IV**：技能库检索、自我验证、自动课程。**DV**：解锁里程碑速度、独特物品数、旅行距离、新世界泛化。
- **主要结论**：独特物品 3.3×、旅行距离 2.3×、里程碑解锁快 15.3×；技能库在新世界可迁移解决新任务——技能库是泛化关键。
- **证据强度**：强实证（Minecraft 开放环境，连续多世界实验）。
- **研究局限**：环境特定（Minecraft）；依赖强模型（GPT-4）；技能以代码表示，非通用语义计划。
- **与本项目的关系**：本项目可从每次 replan 沉淀"计划模式库"；"自我验证改进"与 RuleEngine 校验回路一致。
- **可支持的系统设计**：计划模板库（可复用计划结构 + 成功统计），新目标优先检索模板而非重生成；replan 可先试模板再决定是否调 LLM。
- **可采集的数据**：计划模板的复用次数/成功率、每次生成方式（模板 vs LLM）的成本对比。
- **可形成的 User State**：skill_template_coverage（用户目标被模板库覆盖的比例）。
- **可作为系统的哪一部分**：LLM Harness 的模板库（structured memory）——降低 LLM 调用成本的机制。
- **推荐优先级及原因**：★★★★。技能库=结构化记忆减少重复 LLM 调用的最直接证据，与本项目 replan 冷却期需求天然互补。

### [15] MemGPT: Towards LLMs as Operating Systems（arXiv:2310.08560）

- **研究问题**：上下文窗口有限，如何让 LLM 处理远超窗口的长期会话/文档？
- **核心理论**：借鉴 OS 分层内存——LLM 管理"主上下文（主存）+ 外部存储（磁盘）"，用函数调用（self-directed + 中断）在层级间搬运数据；上下文按需分段加载。
- **IV**：内存层级管理、中断机制、工具选择。**DV**：超长文档分析质量、多会话一致性、长期记忆指标。
- **主要结论**：MemGPT 能分析远超上下文窗口的文档，并维持跨会话的长期对话记忆与动态演化（相比固定上下文基线显著更优）。
- **证据强度**：中等偏强（两大任务族实证；系统设计为主，无大规模基准）。
- **研究局限**：内存寻址隐式；函数调用框架定制成本。
- **与本项目的关系**：本项目 User State 与应用数据分开存储、按需注入 prompt 即"分层内存"思想的实现；MemGPT 提供正式机制与中断路径。
- **可支持的系统设计**：LLM 上下文管理协议：固定注入（当前目标+最近反馈+生效规则）与按需加载（历史 replan 摘要、年度统计、长文档证据）分级；超窗时先压缩检索再调用。
- **可采集的数据**：每会话注入/加载的上下文量、窗口使用率、因截断导致的生成失败率。
- **可形成的 User State**：user_context_footprint（用户长期记忆的压缩摘要）。
- **可作为系统的哪一部分**：LLM Harness 的上下文编排层（memory tiers）。
- **推荐优先级及原因**：★★★☆。管线即将做长期 Agent 记忆时的必读，短期对标"上下文按需注入"。

### [16] Let's Verify Step by Step（arXiv:2305.20050，ICLR 2024）

- **研究问题**：训练模型时用"最终答案监督"（outcome supervision）还是"逐步过程监督"（process supervision）更可靠？验证器应从何入手训练？
- **核心理论**：训练过程奖励模型（PRM）对每一步推理打分；提出主动学习采样更有效的标注步；发布 PRM800K（800k 步级人工标签）。
- **IV**：监督类型（outcome vs process）、主动学习采样策略、PRM 训练数据规模。**DV**：MATH 测试集准确率、PRM 与奖励模型的判别力。
- **主要结论**：过程监督显著优于结果监督；PRM 模型解决 MATH 代表性子集 **78%**（当时 SOTA 水平）；主动学习显著提高过程监督效率。**配合测试时搜索（多数投票）还能进一步提升**。
- **证据强度**：强实证（OpenAI 团队、大规模人工标注数据集、严格基准）。
- **研究局限**：需要逐步骤标注（贵）；面向数学推理；搜索时多次采样成本高。
- **与本项目的关系**：验证器应该验证"过程"而非"结果"——类比：RuleEngine 不只校验最终计划是否完整，还要校验每步的前提/时间约束；反馈信号应细化到规则级别。
- **可支持的系统设计**：计划验证器分层——硬规则查每步合法性（对应 process supervision），ROI/目标可达性查整体（outcome）；执行反馈分步骤采集（plan_repair 节点用步骤级失败修正）。
- **可采集的数据**：步骤级执行状态（每任务完成/卡住）+ 最终完成率 → 训练步骤级成功率预测模型（PRM 类比）。
- **可形成的 User State**：step_failure_pattern（用户卡住的步骤类型分布）。
- **可作为系统的哪一部分**：ML 层（步骤成功率预测器=统计 PRM）；真正意义上进入"验证器"子问题核心。
- **推荐优先级及原因**：★★★★★。验证器设计的分水岭论文，直接指导 RuleEngine 的"分步校验 + 主动学习采集反馈"。

### [17] PlanBench: An Extensible Benchmark for Evaluating LLMs on Planning and Reasoning about Change（arXiv:2206.10498，NeurIPS 2023 D&B）

- **研究问题**：如何系统、可扩展地评估 LLM 的真实规划能力（而非常识检索）？
- **核心理论**：用 IPC（国际规划竞赛）风格规划域（Blocksworld、logistics 等）构造可扩展基准；单实例自动生成大量测试——用于衡量"规划 vs 检索"的真伪。
- **IV**：模型规模/家族、任务域（Blocksworld 等）、是否需要基数/推理能力类型。**DV**：计划正确性（plan validity）、错误类型分布。
- **主要结论**：即便 SOTA 模型，计划生成等关键能力仍远未达标；LLM 表现对问题规模（更多块）急剧退化；常混淆"回答模型训练数据里见过的结论"与"真规划"。
- **证据强度**：强实证基准（持续被后续研究作标准评估工具）。
- **研究局限**：域数量有限；2022 基准年代模型较旧（作者及后续论文持续更新）。
- **与本项目的关系**：为本项目"LLM 计划必须由权威校验"提供最直接证据——LLM 计划在经典域即可失败，何况开放域。
- **可支持的系统设计**：把 RuleEngine 校验结果做成"计划有效性 + 错误类型"度量（validity + debug info），作为所有迭代方法（prompt/refine/replan）的统一反馈信号。
- **可采集的数据**：计划有效性、错误类别（前提不满足/目标未达/死锁）统计；问题规模 vs 通过率曲线。
- **可形成的 User State**：plan_failure_type_profile（用户计划失败的主导类型）。
- **可作为系统的哪一部分**：RuleEngine 的错误分类 schema + 评测基准。
- **推荐优先级及原因**：★★★★★。规划可靠性研究的共同参照物，其"有效性检查"思想即本项目 RuleEngine 的学术范本。

### [18] LLMs Still Can't Plan; Can LRMs? A Preliminary Evaluation of OpenAI's o1 on PlanBench（arXiv:2409.13373）

- **研究问题**：OpenAI o1（超大推理模型 LRM）在 PlanBench 上是否突破自回归 LLM 的规划上限？
- **核心理论**：用 PlanBench（含难度扩展：blocksworld 加零、自由变量）考察 o1；区分"答案可用性"与"正确率"，关注效率与保证。
- **IV**：模型类型（o1 vs 其他 LLM）、问题规模、推理预算。**DV**：PlanBench 成功率、成本（token）、效率。
- **主要结论**：o1 较传统 LLM 是数量级提升（量子跃迁级），但远未饱和；提高推理预算边际收益递减；高部署成本下"保证/效率"问题突出——不可信的模型即使更好仍需仲裁。
- **证据强度**：中等偏强（单一模型族初步评测，未同行评审，但方法严谨并被广泛引用）。
- **研究局限**：仅一个 LRM 家族；评测窗口（2024-09）；成本随预算非线性。
- **与本项目的关系**：强化"即使模型更强，也不可信任其计划可直接执行"——必须保留 RuleEngine + Scheduler 权威仲裁。
- **可支持的系统设计**：模型升级评估流程（换新模型前先在内部 PlanBench 风格测试上离线验证）；推理预算上限与成本护栏。
- **可采集的数据**：模型版本 × 计划有效性 → 决定何时切换默认模型。
- **可形成的 User State**：无直接关系（模型侧而非用户侧）。
- **可作为系统的哪一部分**：评测层（模型选型门禁）。
- **推荐优先级及原因**：★★★★。给"更强的模型也不能免除校验"提供最新证据，直接抑制"换大模型即万事大吉"的期望。

### [19] Can Large Language Models Reason and Plan?（arXiv:2403.04121，Annals NYAS 2024）

- **研究问题**：LLM 到底能不能推理与规划？为什么大量吹捧性结论是误导？
- **核心理论**：论证自回归 LLM 本质上不能自主规划或自我验证（验证也是推理）；指出评测误导来源（用例选择、允许的自我纠正、基线上限）；主张 LLM 宜作为"通用近似知识源 + 翻译器/生成器"，规划交给外部符号求解器与验证器。
- **IV**：评测设置（是否报告首轮准确率、基线上限）。**DV**：规划任务准确率、宣称 vs 实际能力差距。
- **主要结论**：与 LLM-Modulo（[20]）一致的立场：LLM 无内在规划能力，其价值在生成候选与翻译，验证必须外部化。
- **证据强度**：意见/立场论文（权威作者、跨论文元分析），证据间接但系统。
- **研究局限**：立场文性质，非新实验；对"规划"的定义争议仍在。
- **与本项目的关系**：本项目架构（LLM 输出仅候选、RuleEngine 唯一权威）与该立场完全一致——这是一份"架构合法性"背书文献。
- **可支持的系统设计**：无新机制，但用于说服性与评审文档中证明架构合理性；强化 llm-as-candidate 的角色边界。
- **可采集的数据**：重申"首轮准确率 vs 修正后"分开统计——采集 LLM 原始输出（未修）正确率作为独立指标。
- **可形成的 User State**：无。
- **可作为系统的哪一部分**：方法论/立场支撑（避免 LLM 自我校验的陷阱）。
- **推荐优先级及原因**：★★★★★。是"LLM 输出必须过验证器"体系的奠基性评论，几乎本项目架构宣言。

### [20] LLM-Modulo: LLMs Can't Plan, But Can Help Planning in LLM-Modulo Frameworks（arXiv:2402.01817，ICML 2024）

- **研究问题**：既然 LLM 不能规划，它在外置验证器的框架里应扮演什么角色？如何双向耦合 LLM 与符号器？
- **核心理论**：**LLM-Modulo 框架**：LLM 生成候选 + 外部模型化验证器（校验约束/可达性/一致性）双向紧密交互（生成→验证→反馈→再生成）；验证器模型本身可借助 LLM 从知识库/经验构建。
- **IV**：验证器类型/严格度、LLM-验证器交互轮数、问题表示松紧度。**DV**：最终计划满足全部硬约束的比例、迭代轮次、成功解决率。
- **主要结论**：紧耦合的"LLM 生成 + 外部验证"优于单向 pipeline；也优于纯 LLM 提示；验证器由工程知识构造（或 LLM 辅助构造）时适用面更广。
- **证据强度**：中等偏强（主要案例：Blocksworld 数据集+KG-verifier；框架论文，含多个领域案例）。
- **研究局限**：验证失败信息如何反哺生成仍是提示工程依赖；验证器不完备时框架失效。
- **与本项目的关系**：**本项目架构的直接学术名称**——LangGraph 生成候选 → RuleEngine 校验 → 反馈 → replan，即 LLM-Modulo 实例化。
- **可支持的系统设计**：双向反馈协议：RuleEngine 返回机器可读的"失败原因 + 违规步骤"，注入 replan prompt（结构化批评，优于自由文本）；验证器可增量扩展。
- **可采集的数据**：生成-验证-再生成迭代轮数、每轮违规数下降曲线（验证框架收敛性指标）。
- **可形成的 User State**：validate_feedback_utilization（用户目标迭代中每轮计划的违规减少幅度）。
- **可作为系统的哪一部分**：整个 harness 的顶层架构理论；rule_validation ↔ plan_repair 的接口规范。
- **推荐优先级及原因**：★★★★★。与本项目设计蓝图一一对应的论文，直接可引为架构依据。

### [21] Self-Refine: Iterative Refinement with Self-Feedback（arXiv:2303.17651，NeurIPS 2023）

- **研究问题**：同一个 LLM 先自评再自改（无外部监督、无训练）能否提升输出质量？
- **核心理论**：单模型三角色（generator/feedback provider/refiner）迭代循环；反馈需结构化（要点列表）供精炼使用。
- **IV**：迭代轮数、反馈结构、任务类型、模型（GPT-3.5/ChatGPT/GPT-4）。**DV**：人类偏好率、自动指标、绝对任务分。
- **主要结论**：7 个任务上平均提升约 **20%**（绝对）；此时 GPT-4 也能被自身迭代进一步改进。
- **证据强度**：强实证（7 任务、人类评估 + 自动指标）。
- **研究局限**：改进主要出现在"文本生成型"任务；对"事实性错误"类任务迭代常失败（与 [11] CRITIC 结论呼应：无外部验证的自省易空转）。
- **与本项目的关系**：plan_repair 节点可借鉴"结构化反馈清单"格式；但其"自省可能空转"的教训支持本项目把反馈锚定在 RuleEngine 违规项。
- **可支持的系统设计**：replan prompt 要求给出逐条"审计清单→修订 diff"；对事实类错误（如与用户时间表冲突）禁止仅靠自省——必须引用规则原文。
- **可采集的数据**：迭代轮数与计划有效性的关系曲线（自省增益衰减点）。
- **可形成的 User State**：self_refine_gain（该用户目标的迭代增益）。
- **可作为系统的哪一部分**：plan_repair 的 prompt 设计模板（feedback format）。
- **推荐优先级及原因**：★★★★。给出"生成-批判-精炼"标准循环及其边界（哪些任务自省无效）。

### [22] Reflexion: Language Agents with Verbal Reinforcement Learning（arXiv:2303.11366，NeurIPS 2023）

- **研究问题**：Agent 不更新权重，如何从试错中快速学习并保持跨回合记忆？
- **核心理论**：**言语强化学习**——成功/失败反馈转成情景记忆（episodic memory）中的反思文本，下回合注入 prompt 引导决策；支持标量或自由文本、外部或内模拟反馈。
- **IV**：反馈类型/来源、记忆缓冲形式、任务域（决策/编码/推理）。**DV**：任务成功率（如 HumanEval pass@1）。
- **主要结论**：HumanEval pass@1 达 **91%**，超过当时 GPT-4 的 80%；多域一致超基线；最有效的记忆是"经验总结"而非完整轨迹。
- **证据强度**：强实证（多域、消融反馈形式）。
- **研究局限**：依赖反馈信号可得；多轮成本线性；反思质量影响学习。
- **与本项目的关系**：本项目执行反馈 → replan 即是 Reflexion 循环；"压缩为反思摘要"策略可直接用于 ReplanEvent 内容设计。
- **可支持的系统设计**：把执行反馈压缩成结构化"反思记录"（做了什么、为什么失败、下次应避免），作为 replan 的 memory 注入；按用户维护反思缓冲。
- **可采集的数据**：反思文本、反思所指失败原因、采纳反思后的计划成功率变化。
- **可形成的 User State**：reflection_memory（最近 N 条反思摘要）、reflection_utilization。
- **可作为系统的哪一部分**：LLM Harness 的 episodic memory 层 + plan_repair prompt。
- **推荐优先级及原因**：★★★★★。把执行反馈变成"记忆"的标准方法，与本项目 replan 数据流直接对接。

### [23] Tree of Thoughts: Deliberate Problem Solving with LLMs（arXiv:2305.10601，NeurIPS 2023）

- **研究问题**：只靠贪心左到右解码的 LLM 如何做需要探索/前瞻/回溯的任务？
- **核心理论**：ToT——把推理拆为"thought"单元，对每个中间状态并行采样多种 thought，LLM 自评（打分/投票）引导搜索（BFS/DFS），支持前瞻与回溯。
- **IV**：搜索策略、自评方式（打分 vs 投票）、thought 粒度。**DV**：任务成功率（Game of 24 等）、搜索开销。
- **主要结论**：Game of 24 成功率从 CoT 的 4% 提到 **74%**；创作写作与填字游戏同样大幅提升。自评是搜索引导的关键信号。
- **证据强度**：强实证（三任务、消融）。
- **研究局限**：token 开销大（多路径×多步）；自评分数不可靠时搜索失效；任务需显式可评估中间态。
- **与本项目的关系**：plan 生成可视为计划空间的搜索；本项目以 RuleEngine 替代"LLM 自评"作为分支打分层——更确定、更便宜。
- **可支持的系统设计**：计划候选多路径生成 + RuleEngine 打分剪枝（beam search over plans），失败路径上的违规信息可提前终止无望分支（early pruning）——等价于 ToT+外部值函数。
- **可采集的数据**：每分支的规则违规数（作为剪枝信号质量指标）、搜索宽度 vs 生成质量。
- **可形成的 User State**：branch_score_spread（候选计划质量离散度，不确定性代理）。
- **可作为系统的哪一部分**：plan_generation 的搜索策略（MoE/beam）与 RuleEngine 打分层。
- **推荐优先级及原因**：★★★★。给"让规则引擎当搜索值函数"提供方法论支撑，提升 plan 生成覆盖率。

### [24] AdaPlanner: Adaptive Planning from Feedback with Language Models（arXiv:2305.16653）

- **研究问题**：LLM Agent 如何适应环境反馈动态修订计划（含 plan 中/plan 外两种修订）？
- **核心理论**：闭环比之前向；提出**plan-in/plan-out 修订**策略 + **代码风格 prompt 结构**缓解幻觉 + **技能发现**（把成功计划当 few-shot 示例，降低示例需求）。
- **IV**：修订策略类型、prompt 结构（代码风格 vs 自然语言）、技能发现开关。**DV**：ALFWorld/MiniWoB++ 成功率、所需样本数。
- **主要结论**：SOTA 基线之上 ALFWorld +3.73%、MiniWoB++ +4.11%，且所需样本少 2×/600×；代码风格 prompt 显著降低幻觉。
- **证据强度**：中等偏强（两交互环境、多模型消融）。
- **研究局限**：环境有界；代码风格 prompt 对复杂任务的组织成本。
- **与本项目的关系**：plan_repair 的"in-plan（局部改开关一个任务）vs out-of-plan（重构整体）"二分法可直接映射本项目 replan 粒度决策。
- **可支持的系统设计**：replan 分两级：小偏差=局部修订（不重跑全图）；大偏差=全量重新规划；把计划模板结构化（代码风格 schema）强制 LLM 输出一致字段。
- **可采集的数据**：修订类型分布（局部 vs 全量）、各自成功率与成本。
- **可形成的 User State**：deviation_magnitude（执行偏差的历史均值，决定下次修订级别）。
- **可作为系统的哪一部分**：plan_repair 节点分级策略 + 计划输出 schema 约束。
- **推荐优先级及原因**：★★★★。给出"何时小修、何时大改"的可操作粒度策略——本项目 replan 冷却期与分级修订的结合点。

### [25] Flexible and Efficient Grammar-Constrained Decoding（arXiv:2502.05111，ICML 2025）

- **研究问题**：如何让 LLM 生成"保证满足 CFG 语法"的结构化输出，同时预处理/在线掩码高效？
- **核心理论**：grammar-constrained decoding（GCD）——用 CFG 掩码惩罚必然违规 token，从**保证**层面杜绝语法错误；提出新的子词-文法对齐算法：预处理比现有方法快 17.71×，在线掩码保持 SOTA 效率。
- **IV**：文法复杂度、tokenizer 对齐算法、实现。**DV**：预处理时间、在线掩码速度、输出合法率。
- **主要结论**：语法合法率 100%（保证语义）；预处理提速 17.71×，适合频繁切换 schema 的生产场景。
- **证据强度**：中等偏强（系统论文；形式保证 + 基准对比）。
- **研究局限**：只保证语法、不保证语义约束（如业务规则跨界）。
- **与本项目的关系**：计划 JSON 输出可先受 GCD 保证字段结构合法，RuleEngine 再专心查语义硬约束——两层校验分工（语法层 vs 语义层）。
- **可支持的系统设计**：为 PlanCandidate/PlanningState 定义 pydantic/CFG schema，接 GCD 解码器（如 SD-JT/outlines/xgrammar 同类技术）强制输出成型；RuleEngine 只处理规则语义。
- **可采集的数据**：非法输出占比（GCD 前后对比）、schema 切换频率。
- **可形成的 User State**：无直接关系。
- **可作为系统的哪一部分**：LLM Harness 的输出层（constrained generation 强制器）。
- **推荐优先级及原因**：★★★★。把"LLM 输出格式 100% 合法"从 prompt 劝告变成形式保证，成本极低收益极高。

### [26] Chain-of-Thought Prompting Elicits Reasoning in Large Language Models（arXiv:2201.11903，NeurIPS 2022）

- **研究问题**：提供中间推理步骤示例能否激发大模型复杂推理能力（涌现）？
- **核心理论**：CoT——prompt 中给出"思考步骤"示例；推理能力在**足够大规模**模型上涌现（小模型无效）。
- **IV**：模型规模（8B-540B）、示例数量、任务类型（算术/常识/符号）。**DV**：GSM8K、SVAMP、CSQA 等准确率。
- **主要结论**：540B PaLM 用 8 个 CoT 示例在 GSM8K 达当时 SOTA，超过带 verifier 微调的 GPT-3；推理能力随规模涌现。
- **证据强度**：强实证（三模型的规模效应曲线）——但这正是"更大模型≠好规划"的划界文献。
- **研究局限**：小模型无效（规模依赖）；多步推理误差会累积。
- **与本项目的关系**：plan 生成 prompt 应内含"约束检查链"示例；同时警示：让 LLM 输出"计划推导过程"可能只是能力涌现的演示，不构成正确性保证。
- **可支持的系统设计**：plan_generation 节点的 few-shot 模板（含 1 个"先列约束→再排步骤→再自查"示例）；把 CoT 显式作为候选推理轨迹记录用于审计。
- **可采集的数据**：有无 CoT 示例时计划有效性与失败模式的差异。
- **可形成的 User State**：无。
- **可作为系统的哪一部分**：prompt 工程基线（Harness prompt 设计）。
- **推荐优先级及原因**：★★★★。范式基础文，关系到 plan 节点 prompt 设计的出发点；并提示规模假设需实证。

### [27] Self-Consistency Improves Chain of Thought Reasoning in Language Models（arXiv:2203.11171，ICLR 2023）

- **研究问题**：对同一问题采样多条推理路径后"多数投票"，能否显著提升 CoT 的可靠性？
- **核心理论**：自洽性——采样多样推理路径（temperature>0），对最终答案边际化/投票取一致；直觉：复杂问题有唯一正确回答、多条正确思路。
- **IV**：采样数（k）、temperature、任务族。**DV**：GSM8K/SVAMP/AQuA/StrategyQA/ARC 准确率。
- **主要结论**：GSM8K **+17.9%**、SVAMP +11.0%、AQuA +12.2%、StrategyQA +6.4%、ARC-challenge +3.9%——即"多次采样+一致性"是最强解码策略之一。
- **证据强度**：强实证（5 基准、多模型规模）。
- **研究局限**：成本 = k×；只在答案可投票的任务上有效（开放式计划不适合投票）；未解决"共同错误方向"。
- **与本项目的关系**：计划没有唯一"答案"，但**候选计划一致性**可作不确定性信号——多个采样计划分歧大 = 该目标不适合 LLM 直出，值得规则/人工介入（高 uncertainty → 路由/拒绝）。
- **可支持的系统设计**：低风险方式：对 plan 生成做 k=2-3 次采样，用 RuleEngine 投"通过/不通过"并进行多数裁决（rule-as-voter）；候选分歧度进 uncertainty 特征。
- **可采集的数据**：k 采样的分歧度与最终执行成功率的联合分布（校准 uncertainty）。
- **可形成的 User State**：plan_uncertainty（用采样分歧度估计）。
- **可作为系统的哪一部分**：ML 层 uncertainty 估算 + LLM Harness 的采样策略。
- **推荐优先级及原因**：★★★★。采样-投票是成本换可靠性的经典手段，且为本项目提供可操作的"不确定性→是否升级 LLM"信号。

### [28] Mixture-of-Agents Enhances Large Language Model Capabilities（arXiv:2406.04692）

- **研究问题**：多个 LLM 的输出互相作为上下文提示，能否涌现超过最强单模型的协作结果？
- **核心理论**：分层 MoA——每层多个 agent，各自把上一层全部输出作为辅助信息再生成；层间传递聚合。
- **IV**：层数、每层 agent 数、聚合策略（proposer/aggregator 分工）。**DV**：AlpacaEval 2.0 / MT-Bench / FLASK 得分。
- **主要结论**：开源模型 MoA 达 AlpacaEval 2.0 **65.1%**，超 GPT-4 Omni（57.5%）；协作收益随层数增多。
- **证据强度**：强实证，但主攻开放性写作类评测（AlpacaEval 已被批评易被长度/风格偏置影响）。
- **研究局限**：成本极高（多层多 agent）；写作/对话类任务优势明显，推理类收益存疑；与"降低 LLM 调用成本"目标相反。
- **与本项目的关系**：反面参照：本项目追求成本最优，MoA 的多模型堆叠成本策略只适用于"单次高价值决策且预算充裕"场景（如复杂规划的一次性重规划），不适合作默认管线。
- **可支持的系统设计**：仅保留"聚合多候选"的轻量形态：不同节点输出的多个候选计划交给 RuleEngine 择一（rank 而非 generate-ensemble）。
- **可采集的数据**：多候选方案的偏好数据（哪些候选被采用及其执行结果）。
- **可形成的 User State**：preferred_plan_shape（用户历史采纳计划的风格）。
- **可作为系统的哪一部分**：论文主要作为成本策略的对照组写入设计文档。
- **推荐优先级及原因**：★★☆。方向相反（堆模型而非省模型），作为反驳参照及"何时真的值得多模型"的边界案例。

### [29] AgentBench: Evaluating LLMs as Agents（arXiv:2308.03688，ICLR 2024）

- **研究问题**：LLM 做 Agent 到底行不行？在哪些交互环境、哪些能力上掉链子？
- **核心理论**：8 个环境多维基准（代码、游戏、Web、推理…）系统评估 LLM-as-Agent 的推理与决策。
- **IV**：模型（API vs 开源 ≤70B）、Agent 框架（ReAct 等）。**DV**：各环境任务成功率、失败原因归类。
- **主要结论**：顶级商业模型在复杂环境表现强，但与开源小模型差距巨大；失败主因是**长期推理、决策与指令跟随**不足——正是"多步规划闭环"痛点。
- **证据强度**：强实证（大规模多模型评测），ICLR 2024。
- **研究局限**：环境模拟与真实业务差距；评测随时间折旧。
- **与本项目的关系**：量化了"LLM 在长流程规划中会失败"的普遍性，支撑本项目"减少每步对模型能力的依赖、用结构与规则兜底"。
- **可支持的系统设计**：为本项目建立"轻量 AgentBench"：用固定目标集回归测试 harness 变更（改 prompt/规则之后跑回归）——防退化。
- **可采集的数据**：目标交付成功率作为 harness 级 DV；每类失败频次。
- **可形成的 User State**：aggregate_agent_skill（该用户的 Agent 端任务完成画像）。
- **可作为系统的哪一部分**：评测层（回归测试集）。
- **推荐优先级及原因**：★★★★。提供"LLM 长程任务不可靠"的实证基线，并给出评测框架范本。

### [30] WebArena: A Realistic Web Environment for Building Autonomous Agents（arXiv:2307.13854，ICLR 2024）

- **研究问题**：真实感 Web 环境中，语言 Agent 能完成多少日常任务？差距在哪？
- **核心理论**：含电商/论坛/开发/内容管理四类真实功能网站的环境 + 812 项任务基准，评测端到端功能正确性（非表面匹配）。
- **IV**：Agent 方法（GPT-4 基线、ReAct 等）、任务复杂度。**DV**：端到端任务成功率。
- **主要结论**：最佳 GPT-4 Agent 成功率仅 **14.41%** vs 人类 **78.24%**——长程真实任务上当前 LLM Agent 远未合格。
- **证据强度**：强实证（权威环境，ICLR 2024，被大量复用作测试床）。
- **研究局限**：Web 域限定；成本高。
- **与本项目的关系**：本项目每天真实交付计划并追踪执行——与 WebArena 同级"真实闭环"野心；结果提醒：端到端成功率低是常态，需用 harness 工程（规则+调度+反馈）而非纯模型提升。
- **可支持的系统设计**：端到端执行率作为项目北极星指标；任务难易分层公布（预期各层成功率），避免对 LLM 的过度承诺。
- **可采集的数据**：任务完成率、完成质量（部分完成度）分层统计。
- **可形成的 User State**：execution_completion_distribution。
- **可作为系统的哪一部分**：评测/指标层。
- **推荐优先级及原因**：★★★☆。实证颗度大，说明"闭环成功率"的合理预期；为项目指标设计提供校准。

### [31] GAIA: A Benchmark for General AI Assistants（arXiv:2311.12983）

- **研究问题**：通用 AI 助手（须工具、多模态、推理、Web 浏览结合）能否达到人类级鲁棒性？
- **核心理论**：466 个"对人类简单、对 AI 难"的真实问题集；强调**能力组合**（reasoning + tool use 等）而非单项难度；留 300 题做排行榜防过拟合。
- **IV**：是否配工具/插件、模型家族。**DV**：准确率（人类 92% vs GPT-4+plugins 15%）。
- **主要结论**：人类 92% vs GPT-4 插件版 15%——组合能力是当前 AI 助手最大短板。
- **证据强度**：中等（基准发布论文，非机制研究；但数据集被社区广泛采用）。
- **研究局限**：答案二元判定粗粒度；偏工具配合而非规划……
- **与本项目的关系**：GAIA 的"能力组合"视角与本项目"LLM+规则+预测器+调度器"的组合架构同频——验证了复杂任务需要多模块协作而非单模型。
- **可支持的系统设计**：集成测试集（用真实用户目标构造 GAIA 风格小集）检验 harness 整体增益；端到端 vs 各模块单独评测分离。
- **可采集的数据**：组合任务 vs 单一能力任务的成功率差（harness 增值量化）。
- **可形成的 User State**：复合任务占比（用户目标中需多模块能力组合的比例）。
- **可作为系统的哪一部分**：评测设计参照。
- **推荐优先级及原因**：★★★。作为"组合能力评估"的方法学参考；不与运行时直接耦合。

---

## 四、四子问题结论速览（给实现者的直接指引）

1. **何时不该调 LLM**（[1][2][3][5][6][12][17][18]）：先走确定性 pipeline（Rule/Scheduler/形式化求解）；LLM 仅当（a）目标模糊需语义理解，（b）规则+模板覆盖不足，（c）简单模型+规则校验失败才升级；用采样分歧度（[27]）做"要不要升级"的不确定性信号；宁可 abstention 也不硬编（[6]）。
2. **如何用外部模块辅助 LLM**（[8][9][10][13][15][20]）：prompt 注入结构化上下文（User State、规则 schema、工具结果、检索到的历史成功计划）；要求 LLM 显式引用工具输出（grounding）并禁止它碰 DB（本项目已有约束）；历史经验按语义检索后作 few-shot（[13][14]）。
3. **如何验证 LLM 计划**（[11][16][17][20][21][25][26]）：外部验证器 > 内部自省（[11][19]）；验证要按"步骤级"分解（[16]）；RuleEngine 失败信息以机器可读结构化批评回灌 replan（[20]）；输出层用 GCD 保证语法合法（[25]）；计划有效性 + 错误类别作为统一反馈信号（[17]）。
4. **如何降本**（[1][2][3][4][7][14][27][28]）：任务级路由+级联+阈值校准（[1][2][3][5]）；前缀 KV 缓存与模板复用（[7][14]）；采样-投票只用在关键决策（[27]）；MoA 堆叠成本策略作为对照，避免默认启用（[28]）；先建 mini-RouterBench 离线验证路由划算再上线（[4]）。