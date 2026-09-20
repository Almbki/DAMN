# 方向1：精力/疲劳（Energy / Fatigue）文献调研

> **检索方式**：Europe PMC REST API（www.ebi.ac.uk/europepmc，12 组检索式：ABSTRACT:"mental fatigue" AND "task performance" / "mental fatigue" AND "systematic review" / mental fatigue meta-analysis / TITLE:"subjective energy" / TITLE:"energy level" / "cognitive fatigue" AND "self-report" / mental fatigue AND "academic performance" / fatigue AND learning AND memory / "ego depletion" AND "task performance" / vigor AND fatigue AND "Profile of Mood States" / fatigue AND motivation AND "cognitive performance" / TITLE:"mental energy" OR "subjective vitality"），数据库累计命中约 7 671 条，实际抓取并逐条评估候选 **270 条**，最终采纳 **24 篇**。
> **检索 270 篇（候选池），采纳 24 篇**。
> **验证**：全部采纳文献的 DOI 已通过 `https://doi.org/<DOI>` 实际请求验证可访问（46/48 直接返回 200，2 篇 PLOS 跟随重定向后 200；验证记录见 `docs/research/DOI链接验证记录.txt`）；作者/卷期/页码来自 Europe PMC 元数据。原始检索结果与摘要文本保存在 `api/` 目录，可复核。
> **筛选原则**：优先 peer-reviewed / systematic review / meta-analysis；优先可被系统观测（task logs、completion time、self-report、diary、ESM）的变量；EEG/fMRI/HRV 类研究保留理论价值并明确标注"需传感器"。

---

## 一、采纳文献清单（GB/T 7714）

[1] PESSIGLIONE M, BLAIN B, WIEHLER A, et al. Origins and consequences of cognitive fatigue[J]. Trends in Cognitive Sciences, 2025, 29(8): 730-749.

[2] VAN CUTSEM J, MARCORA S, DE PAUW K, et al. The effects of mental fatigue on physical performance: A systematic review[J]. Sports Medicine, 2017, 47(8): 1569-1588.

[3] SMITH M R, CHAI R, NGUYEN H T, et al. Comparing the effects of three cognitive tasks on indicators of mental fatigue[J]. The Journal of Psychology, 2019, 153(8): 759-783.

[4] SUN H, SOH K G, ROSLAN S, et al. Does mental fatigue affect skilled performance in athletes? A systematic review[J]. PLoS ONE, 2021, 16(10): e0258307.

[5] KOK A. Cognitive control, motivation and fatigue: A cognitive neuroscience perspective[J]. Brain and Cognition, 2022, 160: 105880.

[6] WANG C, DING M, KLUGER B M. Change in intraindividual variability over time as a key metric for defining performance-based cognitive fatigability[J]. Brain and Cognition, 2014, 85: 251-258.

[7] WANG Z, CHANG Y, SCHMEICHEL B J, et al. The effects of mental fatigue on effort allocation: Modeling and estimation[J]. Psychological Review, 2022, 129(6): 1457-1485.

[8] HOLGADO D, SANABRIA D, PERALES J C, et al. Mental fatigue might be not so bad for exercise performance after all: A systematic review and bias-sensitive meta-analysis[J]. Journal of Cognition, 2020, 3(1): 38.

[9] DE JONG M, BONVANIE A M, JOLIJ J, et al. Dynamics in typewriting performance reflect mental fatigue during real-life office work[J]. PLoS ONE, 2020, 15(10): e0239984.

[10] HERLAMBANG M B, CNOSSEN F, TAATGEN N A. The effects of intrinsic motivation on mental fatigue[J]. PLoS ONE, 2021, 16(1): e0243754.

[11] CHAVALI V P, RIEDY S M, VAN DONGEN H P A. Signal-to-noise ratio in PVT performance as a cognitive measure of the effect of sleep deprivation on the fidelity of information processing[J]. Sleep, 2017, 40(3): zsx016.

[12] OWENS D S, PARKER P Y, BENTON D. Blood glucose and subjective energy following cognitive demand[J]. Physiology & Behavior, 1997, 62(3): 471-478.

[13] KATZIR M, EMANUEL A, LIBERMAN N. Cognitive performance is enhanced if one knows when the task will end[J]. Cognition, 2020, 197: 104189.

[14] FULLER D T, SMITH M L, BOOLANI A. Trait energy and fatigue modify the effects of caffeine on mood, cognitive and fine-motor task performance: A post-hoc study[J]. Nutrients, 2021, 13(2): 412.

[15] CARDINI B B, FREUND A M. More or less energy with age? A motivational life-span perspective on subjective energy, exhaustion, and opportunity costs[J]. Psychology and Aging, 2020, 35(3): 369-384.

[16] WOLFF W, SIEBER V, BIELEKE M, et al. Task duration and task order do not matter: No effect on self-control performance[J]. Psychological Research, 2021, 85(1): 397-407.

[17] WANG X, HE X, FU K. Mental fatigue mediates the relationship between qi deficiency and academic performance among fifth-grade students aged 10-13 years[J]. Frontiers in Psychology, 2024, 15: 1369611.

[18] DARNAI G, MATUZ A, ALHOUR H A, et al. The neural correlates of mental fatigue and reward processing: A task-based fMRI study[J]. NeuroImage, 2023, 265: 119812.

[19] CSATHÓ Á, VAN DER LINDEN D, MATUZ A. Change in heart rate variability with increasing time-on-task as a marker for mental fatigue: A systematic review[J]. Biological Psychology, 2024, 185: 108727.

[20] HASSAN E K, JONES A M, BUCKINGHAM G. A novel protocol to induce mental fatigue[J]. Behavior Research Methods, 2024, 56(4): 3995-4008.

[21] SHIEH S F, LU F J H, GILL D L, et al. Influence of mental energy on volleyball competition performance: A field test[J]. PeerJ, 2023, 11: e15109.

[22] WU J, LU F J H, WANG Y, et al. Validation of the athletic mental energy scale for Chinese school-age adolescents[J]. Scientific Reports, 2024, 14: 18038.

[23] SCHAMPHELEER E, HABAY J, PROOST M, et al. Current practices for mental fatigue quantification and induction in movement science: Introducing the SPeCIFY guidelines[J]. Sports Medicine, 2025, 55(10): 2387-2413.

[24] SMALLE E H M, KARANTINOU E, MÖTTÖNEN R. The effects of cognitive fatigue and articulatory suppression on statistical language learning depend on the strength of cognitive resources[J]. Cognitive Science, 2026, 50(2): e70178.

---

## 二、源链接（按上述编号）

1. https://doi.org/10.1016/j.tics.2025.02.005 （Elsevier 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/40169294/
2. https://doi.org/10.1007/s40279-016-0672-0 （Springer 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/28044281/
3. https://doi.org/10.1080/00223980.2019.1611530 （Taylor & Francis 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/31188721/
4. https://doi.org/10.1371/journal.pone.0258307 （PLOS 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/34648555/
5. https://doi.org/10.1016/j.bandc.2022.105880 （Elsevier 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/35617813/
6. https://doi.org/10.1016/j.bandc.2014.01.004 （Elsevier 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/24486386/
7. https://doi.org/10.1037/rev0000365 （APA 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/35511531/
8. https://doi.org/10.5334/joc.126 （Ubiquity 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/33103052/
9. https://doi.org/10.1371/journal.pone.0239984 （PLOS 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/33022017/
10. https://doi.org/10.1371/journal.pone.0243754 （PLOS 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/33395409/
11. https://doi.org/10.1093/sleep/zsx016 （Oxford 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/28364430/
12. https://doi.org/10.1016/S0031-9384(97)00156-X （Elsevier 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/9272652/
13. https://doi.org/10.1016/j.cognition.2020.104189 （Elsevier 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/31978813/
14. https://doi.org/10.3390/nu13020412 （MDPI 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/33525438/
15. https://doi.org/10.1037/pag0000445 （APA 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/32077733/
16. https://doi.org/10.1007/s00426-019-01230-1 （Springer 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/31321518/
17. https://doi.org/10.3389/fpsyg.2024.1369611 （Frontiers 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/38873520/
18. https://doi.org/10.1016/j.neuroimage.2022.119812 （Elsevier 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/36526104/
19. https://doi.org/10.1016/j.biopsycho.2023.108727 （Elsevier 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/38056707/
20. https://doi.org/10.3758/s13428-023-02191-5 （Springer 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/37537491/
21. https://doi.org/10.7717/peerj.15109 （PeerJ 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/36992946/
22. https://doi.org/10.1038/s41598-024-66931-z （Nature Portfolio 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/39098949/
23. https://doi.org/10.1007/s40279-025-02286-3 （Springer 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/40911281/
24. https://doi.org/10.1111/cogs.70178 （Wiley 已验证 200）· https://pubmed.ncbi.nlm.nih.gov/41730120/

---

## 三、逐篇要点整理

### 1. Pessiglione 等 (2025) — 认知疲劳的起源与后果（Trends in Cognitive Sciences 综述）

- **研究问题**：为什么在长时间的认知工作后会出现疲劳？认知疲劳如何影响神经加工与行为决策？
- **核心理论**：提出 **MetaMotiF 概念模型**：疲劳源于认知控制脑区的代谢改变（生物学原因），但通过动机过程影响行为——疲劳提高"认知控制成本"，使决策偏向低努力、即时奖励的选择。
- **IV**：任务时间（time-on-task）、认知任务强度。
- **DV**：自我报告疲劳、行为表现、经济选择（努力-奖励权衡）、生理/神经指标。
- **主要结论**：认知疲劳确实降低后续任务表现并改变努力-奖励权衡；疲劳的主观体验（self-report）是可靠的核心指标；疲劳与"成本感知升高"而非"能力耗竭"直接相关。
- **证据强度**：高（顶刊权威综述，被引 35，2025 年最新框架）。
- **研究局限**：综述性质，模型（MetaMotiF）为整合性假设，部分机制尚待直接验证。
- **与本项目的关系**：为 User State 中"精力/疲劳→行为倾向"的因果链提供理论骨架：疲劳用户更易选择低努力/即时回报行为。
- **支持的系统设计**：计划生成时对高疲劳用户降低任务难度/拆分粒度；反馈回路中把"主观精力下降"作为调整因子。
- **可采集数据**：用户自评疲劳（VAS）、任务完成时长、休息频率、选择偏好（困难任务 vs 简单任务的选择记录）。
- **可形成的 User State**：`mental_fatigue_state`（主观疲劳 + 行为证据合成）、`effort_cost_sensitivity`（成本敏感度）。
- **可成为哪一部分**：LLM Harness 的系统提示背景知识（解释"为什么疲劳用户需要更小任务块"）+ Statistical Model 的疲劳状态转移先验。
- **推荐优先级**：★ 最高。整条证据链的核心理论框架。

### 2. Van Cutsem 等 (2017) — 精神疲劳对体能表现的系统综述（Sports Medicine）

- **研究问题**：精神疲劳是否损害后续体能/耐力表现？机制是什么？
- **核心理论**：精神疲劳的"心理生物学状态"理论（psychobiological state）——疲劳通过提高感知劳累度（RPE）而非生理能力下降来降低表现。
- **IV**：精神疲劳诱导任务（≥30 min 认知任务）vs 控制条件。
- **DV**：耐力表现（力竭时间、自我选择功率/速度、完成时间）、RPE、心率/血乳酸/摄氧量等生理变量。
- **主要结论**：精神疲劳一致地降低耐力表现（力竭时间缩短、完成时间增加），机制是感知劳累度升高；心率、血乳酸等生理变量不受影响；最大力量/无氧能力不受影响。
- **证据强度**：高（系统综述，被引 496，Sports Medicine 顶刊）。
- **研究局限**：纳入研究多为年轻健康男性；运动领域结论外推到认知任务场景需谨慎。
- **与本项目的关系**：直接回答"高认知疲劳是否延长任务完成时间"——是，且机制是主观劳累感知而非能力下降。
- **支持的系统设计**：Duration Predictor 加入疲劳修正项（估计完成时间上浮）；Scheduler 在高疲劳时安排低强度/恢复性任务。
- **可采集数据**：任务前自评疲劳、任务完成时间、用户主观劳累评分（RPE 式 1-10）。
- **可形成的 User State**：`perceived_exertion`、`fatigue_impact_on_duration`。
- **可成为哪一部分**：Rule——"疲劳评分 ≥ 阈值 → 任务时长估计 ×1.2"类硬规则候选；Statistical Model 的疲劳-时长回归先验。
- **推荐优先级**：★ 最高。为"疲劳→完成时间"提供最强证据。

### 3. Smith 等 (2019) — 三种认知任务对精神疲劳指标的影响（The Journal of Psychology）

- **研究问题**：不同认知任务（PVT、AX-CPT、Stroop）诱发精神疲劳的程度与持续时间有何差异？哪种测量最实用？
- **核心理论**：精神疲劳的多指标测量框架（主观 + 行为 + 生理）。
- **IV**：任务类型（45 min PVT / AX-CPT / Stroop vs 中性纪录片）。
- **DV**：主观疲劳（VAS、BRUMS 情绪量表）、3-min PVT 认知表现、EEG、HRV。
- **主要结论**：三种任务均显著提高主观疲劳；**抑制控制类任务（AX-CPT、Stroop）诱发的疲劳比简单警觉任务（PVT）持续更久**（20/50/60 min）；简单 VAS 是评估精神疲劳最实用的工具。
- **证据强度**：中高（随机交叉实验，被引 157）。
- **研究局限**：实验室任务诱发范式；EEG/HRV 效应不显著，提示短期任务的生理标记灵敏度有限。
- **与本项目的关系**：支持"抑制控制/复杂任务消耗精力更多、恢复更慢"的假设——高认知任务更依赖高精力状态。
- **支持的系统设计**：任务分类系统把"需要反应抑制/持续注意"的任务标记为高疲劳负荷；休息时间估计参考疲劳持续时间。
- **可采集数据**：任务前后 VAS 疲劳评分、任务类型标签、任务时长。
- **可形成的 User State**：`task_induced_fatigue_load`（按任务类型累积）。
- **可成为哪一部分**：Rule——任务类型→疲劳累积速率的查表规则；Statistical Model 输入特征。
- **推荐优先级**：★ 高。给出"哪种任务耗精力、多久恢复"的可落地参数。

### 4. Sun 等 (2021) — 精神疲劳是否影响运动员技能表现（PLoS ONE 系统综述）

- **研究问题**：精神疲劳是否损害技能类（非耐力类）运动表现？
- **核心理论**：精神疲劳通过损害执行功能（executive functions）降低技能表现（准确率、决策）。
- **IV**：精神疲劳诱导（认知任务）vs 对照；运动项目（足球、篮球、乒乓球）。
- **DV**：技能表现（准确率、完成时间、技战术决策）、执行功能指标。
- **主要结论**：精神疲劳一致地降低技能表现——准确率下降、执行时间增加；进攻性技能受影响大于防守性技能；机制指向执行功能受损。
- **证据强度**：中高（系统综述，被引 71）。
- **研究局限**：纳入 11 项研究，异质性较高；运动场景。
- **与本项目的关系**：再次确认"精神疲劳→准确率下降 + 完成时间延长"，且指明机制是执行功能（工作记忆/抑制/转换）。
- **支持的系统设计**：高疲劳状态下调低任务的精度要求/复杂度；错误率上升时触发休息建议。
- **可采集数据**：任务错误率、反应时间、任务完成质量指标（日志可观测）。
- **可形成的 User State**：`executive_load`、`fatigue_quality_penalty`（质量惩罚系数）。
- **可成为哪一部分**：Statistical Model——用错误率/RT 序列估计疲劳的函数形式；Rule——疲劳状态下的质量阈值放宽。
- **推荐优先级**：★ 高。为"疲劳→质量下降"提供行为证据。

### 5. Kok (2022) — 认知控制、动机与疲劳：认知神经科学视角（Brain and Cognition）

- **研究问题**：认知控制、动机与疲劳如何在脑网络中交互并统一为一个模型？
- **核心理论**：**成本-收益统一模型**——疲劳提高控制成本，动机（奖励价值）调节净动机价值；奖赏/成本/疲劳在中额前额叶汇聚计算。
- **IV**：动机条件、疲劳状态、任务需求。
- **DV**：行为表现、脑网络连接、成本-收益决策。
- **主要结论**：疲劳降低大脑大规模网络整合（纹状体-皮层通路高成本连接），作为内感受信息进入成本-收益计算；动机可通过多巴胺系统"赋能"网络抵消疲劳影响。
- **证据强度**：中（整合性综述，被引 60）。
- **研究局限**：理论综合性质，具体参数化不足。
- **与本项目的关系**：为"奖励/动机可抵消疲劳"提供机制解释——系统可在疲劳时通过奖励设计维持表现。
- **支持的系统设计**：动机增强模块（疲劳时提高任务的即时奖励/反馈频率）；计划重排时优先安排高内在动机任务。
- **可采集数据**：任务反馈频率、奖励设计参数、完成率对比。
- **可形成的 User State**：`motivation_level`、`reward_sensitivity`。
- **可成为哪一部分**：LLM Harness——生成动机话术/奖励提示的理论依据；Rule——疲劳+低动机→触发激励策略。
- **推荐优先级**：中高。解释"为什么激励有效"，指导干预设计。

### 6. Wang, Ding & Kluger (2014) — 个体内变异性作为认知疲劳敏感指标（Brain and Cognition）

- **研究问题**：相比平均反应时/错误率，个体内反应时变异性（IIV）能否更敏感地反映认知疲劳？
- **核心理论**：疲劳表现为注意力闪失（attentional lapses）而非整体减速——RT 变异性（CV）优于均值。
- **IV**：3 小时连续 cued Stroop 任务中的时间进程（time-on-task）。
- **DV**：RT 变异系数（CV）、平均 RT、准确率、ex-Gaussian 指数成分、MFI 多维疲劳量表。
- **主要结论**：CV 随时间线性上升且效应量显著大于平均 RT 与准确率；CV 变化与 MFI 疲劳分量相关更强；变异性上升反映注意控制崩溃。
- **证据强度**：中高（实验研究，被引 60）。
- **研究局限**：N=15 小样本；实验室任务。
- **与本项目的关系**：**直接可落地**——系统日志里的反应时变异性是比均值更敏感的疲劳信号。
- **支持的系统设计**：从 task logs 计算滑动窗口 RT CV 作为疲劳在线指标；检测到 CV 陡增→触发休息/降载建议。
- **可采集数据**：每次点击/按键的反应时间序列（日志）、任务会话时长。
- **可形成的 User State**：`reaction_time_variability`、`fatigability_slope`。
- **可成为哪一部分**：Statistical Model——疲劳估计的特征工程核心；Rule——CV 超阈值→疲劳状态。
- **推荐优先级**：★ 最高。行为日志即可计算的强指标。

### 7. Wang, Chang, Schmeichel 等 (2022) — 精神疲劳对努力分配的影响：建模与估计（Psychological Review）

- **研究问题**：能否用数学框架建模精神疲劳下个体的努力分配决策？
- **核心理论**：**价值驱动理论 + 半马尔可夫部分可观测模型**——疲劳状态部分可观测，个体以最大化累计主观价值为目标分配努力。
- **IV**：n-back 任务中的自由选择范式（模拟）、疲劳状态动态。
- **DV**：努力分配（任务参与 vs 退出）、任务表现、主观疲劳自报（模型可拟合输入）。
- **主要结论**：提出可估计的疲劳-努力模型框架，能复现疲劳下的表现与参与模式；主观疲劳报告可作观测变量。
- **证据强度**：中（理论建模 + 模拟验证，Psychological Review 权威期刊）。
- **研究局限**：模拟验证为主，待真实数据校准。
- **与本项目的关系**：**直接给出 User State 状态估计的数学模板**——疲劳是隐藏状态，需用行为观测推断。
- **支持的系统设计**：Duration Predictor/User State Estimator 采用状态空间模型（半马尔可夫）+ 行为观测融合；决策引擎按"预期价值最大化"排程。
- **可采集数据**：任务参与/放弃记录、完成情况、自评疲劳。
- **可形成的 User State**：`hidden_fatigue_state`（估计值+置信度）、`effort_allocation_tendency`。
- **可成为哪一部分**：Statistical Model——疲劳-行为的状态空间模型蓝本（可替换/增强现有启发式）。
- **推荐优先级**：★ 最高。为 User State 估计提供可借鉴的数学框架。

### 8. Holgado 等 (2020) — 精神疲劳对运动表现的影响可能没那么严重（Journal of Cognition，偏倚敏感元分析）

- **研究问题**：精神疲劳损害运动表现的证据是否受发表偏倚影响？
- **核心理论**：偏倚敏感元分析（bias-sensitive meta-analysis）——校正发表偏倚后的效应估计。
- **IV**：精神疲劳诱导条件；DV：运动表现、RPE。
- **主要结论**：原始效应 d_z=0.50（小-中），但**校正发表偏倚后降至 0.08 且不显著**——现有证据不足以确证精神疲劳损害运动表现。
- **证据强度**：高（方法严格的元分析，被引 29）。
- **研究局限**：运动领域；分析层面不能排除真实小效应存在。
- **与本项目的关系**：**重要警示**——"疲劳→表现下降"的效应量可能被高估；系统不应把疲劳惩罚系数设得过大，需用自身数据校准。
- **支持的系统设计**：Duration Predictor 的疲劳修正默认保守（小系数），通过在线学习逐步个性化。
- **可采集数据**：个性化疲劳-表现配对数据（用于贝叶斯收缩）。
- **可形成的 User State**：`personal_fatigue_sensitivity`（个体化的疲劳影响系数）。
- **可成为哪一部分**：Rule/Statistical Model——疲劳惩罚参数的先验分布与校准策略；避免硬编码夸大疲劳影响。
- **推荐优先级**：★ 高。防止过度设计（overfitting 到疲劳叙事）。

### 9. de Jong 等 (2020) — 真实办公打字动力学反映精神疲劳（PLoS ONE）

- **研究问题**：能否在无侵入条件下用打字行为动态监测真实办公环境中的精神疲劳？
- **核心理论**：打字动力学（速度、错误率、纠错行为）是疲劳的行为标记；疲劳影响速度-准确率权衡策略。
- **IV**：时间尺度（time-on-task、time-of-day、day-of-week）——6 周连续记录。
- **DV**：打字速度、错误数、纠错行为。
- **主要结论**：早晨先保速度（错误率上升），随后调整策略（速度和准确率双降）；周一/周五偏好速度、其他日偏好准确率；疲劳在日内累积但日间可恢复。
- **证据强度**：中（生态效度高的纵向自然观察，被引 12）。
- **研究局限**：单一机构/打字类任务；无独立疲劳金标准。
- **与本项目的关系**：**这是最直接可复制的数据源**——用用户与系统的交互日志（打字/点击/输入行为）估计疲劳。
- **支持的系统设计**：从输入日志实时计算"速度-准确率权衡偏移"作为疲劳特征；午间/午后疲劳陡增时段自动调整计划密度。
- **可采集数据**：输入速度、退格/纠错频率、点击间隔、会话时长、时钟时间、星期。
- **可形成的 User State**：`input_behavior_fatigue_index`、`diurnal_fatigue_curve`。
- **可成为哪一部分**：Statistical Model——行为-疲劳回归；也可作为 ML 分类器的特征集。
- **推荐优先级**：★ 最高。生态数据直接可用，成本为零。

### 10. Herlambang, Cnossen & Taatgen (2021) — 内在动机对精神疲劳的影响（PLoS ONE）

- **研究问题**：内在动机能否像外在动机一样缓解时间-on-task 疲劳效应？
- **核心理论**：动机调节疲劳效应的认知-动机交互——高内在动机下个体愿意投入更多努力维持表现。
- **IV**：内在动机水平（高/低，通过内容趣味性操纵，Sudoku + 猫视频）。
- **DV**：主观疲劳、任务表现、HRV、瞳孔直径（生理努力）。
- **主要结论**：无论动机水平，疲劳主观报告都随时间上升；但**高内在动机组表现更好、生理努力投入更多、分心更少**——内在动机抵消部分时间效应。
- **证据强度**：中（受控实验 N=28，被引 33）。
- **研究局限**：样本小；Sudoku 单一任务类型。
- **与本项目的关系**：支持"为疲劳用户安排高兴趣/高内在价值任务"的排程策略。
- **支持的系统设计**：Scheduler 把用户偏好的任务类型在疲劳时段优先安排；任务呈现时强化内在价值框架。
- **可采集数据**：任务偏好评分、任务完成质量、投入时长。
- **可形成的 User State**：`intrinsic_motivation_level`（任务级）。
- **可成为哪一部分**：Rule——排程启发式（疲劳→优先内在动机任务）；LLM Harness——任务价值话术生成。
- **推荐优先级**：中高。低成本高收益的排程策略依据。

### 11. Chavali, Riedy & Van Dongen (2017) — PVT 信噪比作为信息处理保真度指标（Sleep）

- **研究问题**：如何最优地表征睡眠剥夺下的认知损伤（PVT 表现）？
- **核心理论**：扩散模型（diffusion model）→ PVT 表现的**信噪比 SNR/LSNR 指标**；反映信息处理保真度。
- **IV**：清醒时长（38 h 总睡眠剥夺）、一天中的时刻。
- **DV**：SNR、LSNR、平均反应速度、失误数（1284 次 PVT 会话，99 人）。
- **主要结论**：所有指标都捕捉到"清醒时长 + 时间-of-day"效应；LSNR 心理测量学性质最优（高灵敏、高稳定、正态性好、无地板/天花板效应）。
- **证据强度**：中高（实验室大样本，被引 22）。
- **研究局限**：睡眠剥夺场景；PVT 特定任务。
- **与本项目的关系**：提供"反应时→认知保真度"的正规化变换公式，可迁移到任何反应时类日志。
- **支持的系统设计**：把用户交互反应时转化为 LSNR 认知指标进入 User State；疲劳风险管理（类似疲劳风险管理系统 FRMS）。
- **可采集数据**：反应时序列（点击/按键）、一天中的时刻、清醒时长代理（起床时间）。
- **可形成的 User State**：`cognitive_fidelity_lsnr`。
- **可成为哪一部分**：Statistical Model——反应时数据的标准变换层；Rule——LSNR 阈值触发恢复性任务。
- **推荐优先级**：中高。指标变换可复用性强。

### 12. Owens, Parker & Benton (1997) — 认知需求后的血糖与主观精力（Physiology & Behavior）

- **研究问题**：认知需求条件下，主观精力与血糖水平的关系是否增强？
- **核心理论**：血糖可用性与主观能量感关联；认知任务消耗加重关联。
- **IV**：认知任务类型（Stroop、快速信息处理、手眼协调任务）。
- **DV**：主观精力/活力、血糖水平（三项研究）。
- **主要结论**：认知需求后血糖下降伴随"感觉更没精力"；主观精力与生理资源存在关联。
- **证据强度**：中（经典三项实验，被引 23，1997 年）。
- **研究局限**：年代久远；机制解释有限（血糖因果性存疑）。
- **与本项目的关系**：支持"主观精力是真实状态的反映，不是纯心理噪音"——自评精力有生理基础，值得作为 User State 输入。
- **支持的系统设计**：把自评精力评分纳入疲劳估计模型；饭后/长时间未进食时段可预期精力低谷。
- **可采集数据**：自评精力（VAS/1-7）、进食时间（可选自报）、任务时间。
- **可形成的 User State**：`subjective_energy`。
- **可成为哪一部分**：Statistical Model——精力-表现回归的自变量；User State 的组成部分。
- **推荐优先级**：中。为自评精力的有效性提供历史证据。

### 13. Katzir, Emanuel & Liberman (2020) — 知道任务何时结束会提升认知表现（Cognition）

- **研究问题**：仅告知任务进度（还剩多少），能否提升表现并减少疲劳？
- **核心理论**：**机会成本理论**——知道任务结束时间降低"分心去其他活动的机会成本"，减少保守努力的需要。
- **IV**：是否提供目标进度反馈（不告知表现质量）。
- **DV**：切换任务表现的渐近水平、主观疲劳、块间休息时长。
- **主要结论**：有进度反馈组表现渐近水平更高、自报疲劳更低、休息更短。
- **证据强度**：中（两个实验，被引 17，Cognition 顶刊）。
- **研究局限**：实验室短任务；未测量长期效应。
- **与本项目的关系**：**直接支持系统 UI 设计**——给用户显示"任务还剩 X 步/预计 Y 分钟"能同时改善表现与疲劳。
- **支持的系统设计**：计划呈现层显示进度条/剩余工作量；Duration Predictor 提供进度估计。
- **可采集数据**：进度展示参数、完成时间、休息间隔、任务间转换延迟。
- **可形成的 User State**：`progress_awareness`（是否处于进度反馈模式）。
- **可成为哪一部分**：Rule/UI——进度反馈开关规则；LLM Harness——阶段性鼓励文案的时机。
- **推荐优先级**：★ 高。零成本干预，直接进入产品设计。

### 14. Fuller, Smith & Boolani (2021) — 特质精力/疲劳调节咖啡因效应的再分析（Nutrients）

- **研究问题**：特质（长期倾向）心理/身体精力与疲劳是否调节咖啡因的认知效应？
- **核心理论**：特质能量-疲劳维度（trait mental/physical energy & fatigue）是稳定个体差异，调节外部干预效果。
- **IV**：特质精力/疲劳水平（量表分组）、咖啡因 vs 安慰剂。
- **DV**：POMS-SF 情绪、状态精力/疲劳、连续减法任务（SS3/SS7）、九孔钉板精细动作。
- **主要结论**：特质精力/疲劳显著调节咖啡因效应——高特质疲劳、低特质精力者获益最大。
- **证据强度**：中（双盲交叉设计再分析，被引 22）。
- **研究局限**：事后分析；咖啡因情境。
- **与本项目的关系**：表明"特质级精力/疲劳"是独立于状态的稳定用户画像维度，值得长期建模。
- **支持的系统设计**：用户画像增加 trait energy/fatigue 维度；干预（如提醒、奖励）强度按特质个性化。
- **可采集数据**：一次性基线量表（POMS-SF 或精简版）、历史表现。
- **可形成的 User State**：`trait_energy`、`trait_fatigue`（慢变量）。
- **可成为哪一部分**：Statistical Model——个体差异的随机效应/分层参数；LLM Harness——个性化激励风格。
- **推荐优先级**：中高。用户画像分层的重要慢变量。

### 15. Cardini & Freund (2020) — 年龄与主观精力/耗竭/机会成本的动机视角（Psychology and Aging）

- **研究问题**：随年龄增长，个体如何理解"精力"？精力耗竭如何影响目标投入？
- **核心理论**：动机的生命全程视角——主观精力（subjective energy）、耗竭（exhaustion）与机会成本（opportunity costs）共同决定目标投入/退出。
- **IV**：年龄（20-92 岁两研究）、体力消耗实验。
- **DV**：精力可用性评价、跨领域精力外溢、主观耗竭与机会成本（多层增长模型）。
- **主要结论**：年龄越大越倾向"精力非有限"观，社会性活动精力更多；但体力消耗后负向跨域外溢更强；耗竭与机会成本是目标退出的动机线索。
- **证据强度**：中（N=276+N=147 双研究，被引 12）。
- **研究局限**：横断面+短期实验；自我报告为主。
- **与本项目的关系**：提示精力概念的多维度性（身体/心理/社交/情绪四域）与"耗竭→退出"机制——系统需区分精力域并监测目标退出倾向。
- **支持的系统设计**：User State 按精力域拆分；检测"高耗竭+高机会成本"时自动调整目标或提供恢复。
- **可采集数据**：分域自评精力（简短量表）、任务放弃/推迟行为。
- **可形成的 User State**：`energy_domains`、`goal_disengagement_risk`。
- **可成为哪一部分**：Statistical Model——精力分域建模；Rule——耗竭阈值触发计划调整。
- **推荐优先级**：中。丰富精力状态的分域结构。

### 16. Wolff 等 (2021) — 任务时长与顺序不影响自我控制表现（Psychological Research，自我损耗无效证据）

- **研究问题**：自我损耗效应是否存在？任务时长/顺序是否是争议来源？
- **核心理论**：力量模型（strength model of self-control）vs 失败的重复验证。
- **IV**：主/次自我控制任务时长（2/4/8/16 min）、任务类型（Stroop/转写）。
- **DV**：次任务表现、主观自我控制需求。
- **主要结论**：**N=709 高功效实验未发现自我损耗效应**——先前自我控制消耗不损害后续表现；任务时长无影响（甚至更长主任务表现略好）。
- **证据强度**：高（高功效预注册式大样本，被引 26）。
- **研究局限**：实验室任务；不能排除真实世界中的细微效应。
- **与本项目的关系**：**重要警示**——"精力损耗→后续任务自动变差"的简单假设不成立；系统不应假定任务排序必然受前一任务耗损影响，疲劳效应主要来自长时段累积而非单次消耗。
- **支持的系统设计**：避免基于"自我损耗"的过度激进的重排逻辑；疲劳修正以长时段累积（time-on-task）为主。
- **可采集数据**：任务时长、任务顺序、后续任务表现（用于自身验证）。
- **可形成的 User State**：`cumulative_load`（累积负荷）而非"瞬时损耗"。
- **可成为哪一部分**：Rule——关于任务排序的约束放松；Statistical Model——区分"单次损耗"与"累积疲劳"效应。
- **推荐优先级**：中高。防止把"自我损耗"神话写进规则引擎。

### 17. Wang, He & Fu (2024) — 精神疲劳中介气虚与学业成绩（Frontiers in Psychology，中国小学生）

- **研究问题**：中医"气虚"与小学生学业成绩的关系是否由精神疲劳中介？
- **核心理论**：健康（中医体质）→ 精神疲劳 → 学业表现的中介模型。
- **IV**：气虚程度（中医体质问卷）、精神疲劳（自评量表）。
- **DV**：数学/语文考试成绩（N=550，五年级，四川）。
- **主要结论**：精神疲劳与数学成绩 r=-0.46、语文 r=-0.34（均 p<0.01）；控制气虚后精神疲劳仍显著预测成绩；对数学的中介强于语文。
- **证据强度**：中（大样本横断面，被引 1，2024 新近）。
- **研究局限**：横断面因果受限；单一地区。
- **与本项目的关系**：**中文场景直接证据**——自评精神疲劳与学业任务表现（考试成绩）显著负相关，支撑"疲劳→完成质量/效率"闭环。
- **支持的系统设计**：任务成绩/完成质量作为疲劳的验证信号；数学类（流体认知）任务对疲劳更敏感，优先调整。
- **可采集数据**：任务得分、自评疲劳、任务类型（数理 vs 语文类）。
- **可形成的 User State**：`self_reported_fatigue`、`quality_sensitivity`。
- **可成为哪一部分**：Statistical Model——疲劳-质量回归的中文场景先验；Rule——数理任务疲劳惩罚更高。
- **推荐优先级**：中高。中文样本 + 学业任务，与产品定位吻合。

### 18. Darnai 等 (2023) — 精神疲劳与奖励加工的神经关联（NeuroImage，fMRI，需扫描设备）

- **研究问题**：额外奖励能否逆转时间-on-task 疲劳导致的表现下降？脑机制是什么？
- **核心理论**：成本-收益评估框架——中额叶回、岛叶、前扣带参与疲劳-奖励权衡。
- **IV**：疲劳诱导（PVT）+ 额外金钱奖励条件。
- **DV**：PVT 表现（RT）、BOLD 激活（右中额叶回/右岛叶/右前扣带）。
- **主要结论**：疲劳降低这些脑区激活与表现；**额外奖励恢复激活与表现**——奖励效应有明确神经基础。
- **证据强度**：中（任务态 fMRI，被引 18）。（⚠️ 需 fMRI 设备，仅理论价值）
- **研究局限**：实验室 fMRI；健康青年。
- **与本项目的关系**：强化"奖励/动机干预在疲劳时可恢复表现"的证据链。
- **支持的系统设计**：疲劳触发奖励机制（积分/成就/即时反馈）的设计依据。
- **可采集数据**：任务完成率、奖励设置参数。
- **可形成的 User State**：`reward_responsiveness`。
- **可成为哪一部分**：LLM Harness——激励策略文案；Rule——疲劳×奖励匹配规则。
- **推荐优先级**：中。机制性支持，无直接数据采集价值。

### 19. Csathó, Van der Linden & Matuz (2024) — HRV 随任务时间变化作为疲劳标记（Biological Psychology 系统综述）

- **研究问题**：心率变异性（HRV）随 time-on-task 的变化能否可靠标记精神疲劳？
- **核心理论**：自主神经系统（副交感活动）随疲劳发展的变化。
- **IV**：长时间认知任务（time-on-task）；（系统综述 19 项研究）。
- **DV**：HRV 各指标（LF、RMSSD 等）。
- **主要结论**：除 2 项外所有研究均发现 HRV 随任务时间显著变化；LF 与 RMSSD 最一致（随疲劳上升）。
- **证据强度**：高（PRISMA 系统综述，被引 23）。（⚠️ 需心率传感设备，可穿戴可选）
- **研究局限**：指标间不一致性高；实验室诱发。
- **与本项目的关系**：可穿戴设备（手表）若可提供 HRV，可作为疲劳估计的辅助信号。
- **支持的系统设计**：可穿戴集成（可选）；HRV 特征进入 Statistical Model。
- **可采集数据**：HRV（RMSSD/LF）——仅当设备支持；time-on-task 时长。
- **可形成的 User State**：`hrv_fatigue_signal`（辅助，置信度加权）。
- **可成为哪一部分**：Statistical Model——多模态融合（行为+HRV）的可选输入。
- **推荐优先级**：中低。设备依赖，作为可选增强。

### 20. Hassan, Jones & Buckingham (2024) — 诱发精神疲劳的新协议（Behavior Research Methods）

- **研究问题**：能否设计生态效度更高、且带客观表现下降证据的精神疲劳诱发协议？
- **核心理论**：多任务（AX-CPT、n-back、心理旋转、视觉搜索）挑战多种执行功能以诱发疲劳。
- **IV**：2 小时四任务组合电池 vs 控制。
- **DV**：主观疲劳评分、任务表现（N=45，19-63 岁）。
- **主要结论**：新协议同时产生显著主观疲劳上升（p<0.001）与客观表现下降（p=0.008）。
- **证据强度**：中高（方法学论文，被引 17）。
- **研究局限**：诱发协议用途；与真实任务疲劳仍有关联性问题。
- **与本项目的关系**：若系统要做 A/B 验证/实验，可用此协议在对照实验里标准化诱发疲劳以评估系统调整效果。
- **支持的系统设计**：实验/评测模块——验证"疲劳感知→计划调整"效果的实验范式。
- **可采集数据**：实验环境下用户主观疲劳 + 多任务表现。
- **可形成的 User State**：（实验验证用）对照疲劳状态。
- **可成为哪一部分**：测试与评估框架（评估 Fatigue-aware Scheduling 的增益）。
- **推荐优先级**：中。主要用于验证而非运行时。

### 21. Shieh 等 (2023) — 运动心理精力预测排球比赛表现（PeerJ，现场测试）

- **研究问题**：赛前"运动心理精力"能否预测实际比赛表现？
- **核心理论**：运动心理能量（Athletic Mental Energy）六维结构——动机、不知疲倦、平静、活力、自信、专注。
- **IV**：赛前夜测量的六维心理精力（81 名大学生排球运动员）。
- **DV**：3 天比赛表现（FIVB 排球信息系统 6 项客观指标）。
- **主要结论**：六维精力均与比赛表现相关；**心理精力预测接球手表现 R²=0.23**——赛前自评精力可预测客观表现。
- **证据强度**：中（现场研究，被引 6）。
- **研究局限**：专项运动；预测效力因位置而异。
- **与本项目的关系**：**直接支持"自评精力→任务完成效率"**——赛前/任务前自评精力对客观表现有显著预测力。
- **支持的系统设计**：任务开始前采集快速精力自评（1 分钟 6 项），进入 Duration Predictor/任务难度选择。
- **可采集数据**：任务前自评精力（6 维度简版）、任务完成时间/质量。
- **可形成的 User State**：`pre_task_mental_energy`（六维或总分）。
- **可成为哪一部分**：Statistical Model——精力→时长/质量的预测特征；LLM Harness——精力对话采集（自然语言解析）。
- **推荐优先级**：★ 高。自评精力预测力的现场证据。

### 22. Wu 等 (2024) — 运动心理能量量表中国青少年版验证（Scientific Reports）

- **研究问题**：AMES 运动心理能量量表能否在中国青少年中有效验证？
- **核心理论**：心理能量（mental energy）六维构念的操作化测量。
- **IV/测量**：729 名 14-18 岁中国青少年完成中文版 AMES（C-AMES）。
- **DV**：因子结构（CFA）、信效度指标。
- **主要结论**：C-AMES 六因子 18 条目模型拟合良好（RMSEA=0.050，CFI=0.962，TLI=0.951）。
- **证据强度**：中（量表验证研究，被引 1）。
- **研究局限**：量表验证本身；效标关联有待建立。
- **与本项目的关系**：**提供中文可用、信效度验证过的精力自评量表**——可直接嵌入用户 onboarding/每日打卡。
- **支持的系统设计**：用户画像/日常状态采集模块采用 C-AMES（18 条或精简版）。
- **可采集数据**：六维精力自评分数（问卷/ESM）。
- **可形成的 User State**：`mental_energy_profile`（六维）。
- **可成为哪一部分**：Rule——量表评分的标准化与阈值；Statistical Model——精力-表现预测的输入特征。
- **推荐优先级**：★ 高。中文量表直接可用。

### 23. Schampheleer 等 (2025) — 精神疲劳量化与诱发的实践指南（Sports Medicine，SPeCIFY）

- **研究问题**：如何统一精神疲劳研究中的诱发与量化方法学？
- **核心理论**：多方法（行为+主观+生理）三角验证；SPeCIFY 报告指南（Settings, Protocol, Confounders, Individuals, Framework, Yield）。
- **IV/方法**：对现有诱发/量化方法的方法学综述。
- **DV**：方法比较（强度/局限）。
- **主要结论**：行为、主观、生理测量各有优劣；推荐多方法结合；任务时长/难度/性质需按个体定制。
- **证据强度**：高（方法学系统综述，被引 13，2025 最新）。
- **研究局限**：指南性质，非实证。
- **与本项目的关系**：为系统内"疲劳量化模块"提供方法学检查清单（测量组合、混淆控制）。
- **支持的系统设计**：疲劳特征工程的方法学参考——主观 VAS + 行为指标组合优于单指标。
- **可采集数据**：多源疲劳信号（自评+行为）的设计准则。
- **可形成的 User State**：`fatigue_measure_battery`（多源融合定义）。
- **可成为哪一部分**：Statistical Model——多模态融合的架构参考。
- **推荐优先级**：中高。保证疲劳测量的严谨性。

### 24. Smalle, Karantinou & Möttönen (2026) — 认知疲劳反而增强统计语言学习（Cognitive Science）

- **研究问题**：认知疲劳与发音抑制对统计语言学习的影响是否取决于个体认知资源？
- **核心理论**：**认知成本假说**——成人执行功能反而限制内隐学习；疲劳削弱执行控制"释放"内隐学习。
- **IV**：认知疲劳（双 n-back）、发音抑制、认知资源高低组（EF 聚类）。
- **DV**：统计语言学习表现（两选一识别，N=50 大学生）。
- **主要结论**：高认知资源组统计学习更差但**从疲劳中获益**；疲劳对学习的效应方向与"任务表现"相反——疲劳不总是坏事。
- **证据强度**：中（多会话实验，被引 1，2026 新近）。
- **研究局限**：单一学习范式；样本小。
- **与本项目的关系**：**非线性警示**——疲劳对"刻意的任务表现"是负面的，但对"内隐/自动化学习"可能中性甚至正向；系统不应一刀切地把疲劳视为全坏。
- **支持的系统设计**：任务类型分级——疲劳时段安排内隐练习型任务（复习/语料浸泡）而非需要执行功能的新知识学习。
- **可采集数据**：任务类型标签（内隐 vs 执行依赖）、疲劳状态、学习效果指标。
- **可形成的 User State**：`task_fatigue_interaction`（任务类型×疲劳交互预测）。
- **可成为哪一部分**：Rule——"疲劳×任务类型"匹配规则（排程启发式）；LLM Harness——任务切换建议的理由生成。
- **推荐优先级**：中高。提供反直觉但重要的排程优化空间。

---

## 四、方向小结（对本项目的综合启示）

1. **疲劳→表现/时长**：精神疲劳确实延长任务完成时间、降低准确率（[2][4]），但效应量可能被发表偏倚高估（[8]），系统应保守起步、在线校准。
2. **最强可观测指标**：反应时个体内变异性 CV（[6]）、打字/输入动力学（[9]）、主观 VAS（[3]）——全部可从 task logs 与轻量自评获得，无需传感器。
3. **高认知任务更依赖精力**：执行功能类任务（抑制、工作记忆）受疲劳影响更大且恢复更慢（[3][4][17]）。
4. **自评精力的预测价值有证据**：赛前自评精力预测客观表现 R²=0.23（[21]）；主观精力有生理基础（[12]）；中文量表 C-AMES 可复用（[22]）。
5. **建模方法**：疲劳是"部分可观测的隐藏状态"，宜用状态空间模型估计（[7]）；疲劳通过"成本感知"而非"能力耗竭"起作用（[1][5]），因此激励/奖励是有效调节手段（[10][18]）。
6. **边界条件**：单次任务损耗效应不可靠（[16]）；疲劳对学习类任务并非全坏（[24]）；知道任务结束时间本身就能提升表现、降低疲劳感（[13]）。
