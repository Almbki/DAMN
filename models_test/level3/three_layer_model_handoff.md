# 三层模型交接文档（Level 1 + Level 2 + Level 3）

## A. 三层模型一句话
- **Level 1**：长期稳定的 Trait（人格倾向）
- **Level 2**：每日动态的 State（疲劳/压力/自我效能，随任务与反思更新）
- **Level 3**：结合 Trait + State + Task + Context + History，预测单任务完成概率和实际耗时

## B. 为什么需要三层
**Who is the user?** (Level 1) → **How is the user now?** (Level 2) → **What will happen on this task?** (Level 3)

Trait ≠ State ≠ Task Outcome。三层逐级解决不同问题，避免把长期特质当成每日状态，也避免直接用特质预测单任务结果而不考虑当下状态和历史经验。

## C. Level 1（Trait Model V1）
- **输入**：IPIP-NEO-120 CAT 回答
- **模型**：Samejima GRM + Bayesian EAP CAT
- **输出**：N/E/O/A/C 的 theta、se、ci95、items_answered
- **验证**：619,150 样本，整体 MAE ~0.198，RMSE ~0.253（详见 `level1/artifacts/cat_validation.json`）
- **状态**：已冻结，只读

## D. Level 2（DDSR-V1）
- **输入**：TaskPlan/TaskExecution + Nightly Reflection（4段） + TraitContext（只读）
- **模型**：AR(1) 先验 + 0-1 网格 Bayes 校正
- **输出**：fatigue/stress/self_efficacy（值+不确定度）、behavioral_indicators、prediction_error、next_day_prior
- **验证**：54 tests passed，13/13 checks true（`level2/level2_validation.json`）
- **状态**：已实现，结构/契约验证完成；无大规模 longitudinal predictive validity 声明

## E. Level 3（Progressive Execution Predictor V1）
- **输入**：Trait（Level1） + pre-task State S_d^-（Level2） + Task + Context + History（真实 TaskExecution）
- **输出**：completion_probability（或null）、predicted_duration_minutes、uncertainty/interval（如可用）、prediction_mode、prediction_status、data_support、feature_snapshot_id、source versions
- **Progressive Prediction**：
  1. **Cold Start**：无足够历史 → duration = estimated_duration，completion_probability = null（不虚造概率）
  2. **History Baseline**：有真实历史 → Beta-Binomial 平滑完成率，中位数实际/预估比值预测时长（相似任务优先）
  3. **Learned Model**：通过 eligibility gate 后启用正则化 Logistic/Ridge；未通过则自动回退到 History Baseline
- **个性化**：随真实历史积累逐渐从 Cold Start → History Baseline →（可选）Learned Model

## F. 总数据流
```mermaid
flowchart TD
    L1[Level 1 TraitProfile V1] --> L3[Level 3 Predictor]
    L2pre[Level 2 pre-task State S_d^-] --> L3
    Task[Task + Context + History] --> L3
    L3 --> Pred[Prediction: P(completion), E(duration)]
    Pred --> Sched[Scheduler/Policy - OUT OF SCOPE]
    Sched --> Exec[Task Execution]
    Exec --> Outcome[Outcome Record]
    Outcome --> L2upd[Level 2 daily update]
    Outcome --> L3hist[Level 3 history/dataset]
    L2upd --> L2next[Level 2 next-day prior]
```

**Prediction Snapshot**：Trait+State(pre-task)+Task+Context+History 冻结；Outcome 单独记录，禁止用 post-task 信息回填。

## G. 输入输出接口示例
**Level 3 Input (概念)**：
```json
{
  "trait": {"theta_n": -0.3, "se_n": 0.27, "...": "...", "model_version": "trait_v1"},
  "state": {"fatigue": 0.4, "fatigue_uncertainty": 0.15, "...": "...", "model_version": "ddsr_v1"},
  "task": {"task_id": "t1", "estimated_duration_minutes": 60, "difficulty": 3},
  "context": {"prediction_timestamp": "...", "time_of_day": 10, "available_time_minutes": 120},
  "history": {"completion_history": [true,false], "duration_ratio_history": [0.8,1.2], "support": {"total_historical_tasks": 2}}
}
```

**Level 3 Output (概念)**：
```json
{
  "completion_probability": 0.65,
  "predicted_duration_minutes": 72.0,
  "uncertainty/interval": "...",
  "prediction_mode": "history_baseline",
  "prediction_status": "ok",
  "model_version": "level3_v1",
  "data_support": {"total_historical_tasks": 10, "usable_duration_samples": 8},
  "feature_snapshot_id": "..."
}
```

## H. 科研边界
- **Level 1**：有大规模官方数据验证（619150 样本）
- **Level 2**：完成结构/两阶段更新与契约验证（54 tests），尚无大规模 longitudinal predictive validity 声明
- **Level 3**：当前无真实 longitudinal outcome dataset，仅验证架构、cold-start、history baseline、anti-leakage、eligibility gate、ablation 框架
- **合成测试 ≠ 预测准确率**；不虚构预测准确率
- **真实使用数据**将用于 Level 3 训练、ablation、个性化

## I. PPT 可直接使用要点
**三层对比表**：
| 层级 | 时间尺度 | 作用 | 输出 |
|---|---|---|---|
| Level 1 | 长期稳定 | 用户画像（Trait） | N/E/O/A/C theta+SE |
| Level 2 | 每日动态 | 当下状态（State） | fatigue/stress/self-efficacy + 不确定度 |
| Level 3 | 单任务预测 | 执行结果预测 | P(completion), E(duration) |

**关键结论（答辩用）**：
1. 三层分离清晰：Trait ≠ State ≠ Outcome
2. Level 3 只做预测，不做调度
3. 冷启动不虚造概率，随历史积累逐渐个性化
4. 严格 anti-leakage（仅用 pre-task state，快照冻结）
5. 工程初始化与学习参数区分，系数未拟合前标记 NOT FITTED
6. Learned Model 需通过 eligibility gate 才启用，否则回退
7. 真实数据缺乏时只声称 IMPLEMENTATION_VALIDATED，不声称 PREDICTIVE_VALIDITY_VALIDATED
