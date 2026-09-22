| 方法 | 路径                               | 说明         | 建议                                    |
| :--- | :--------------------------------- | :----------- | :-------------------------------------- |
| POST | `/api/v1/auth/register`            | 注册         | 保留                                    |
| POST | `/api/v1/auth/login`               | 登录         | 保留                                    |
| POST | `/api/v1/plans/generate`           | 生成首版计划 | 保留，建议 SSE 流式返回                 |
| POST | `/api/v1/plans/{plan_id}/feedback` | 每日快速反馈 | 保留，响应里可带“是否被动触发重排”      |
| POST | `/api/v1/plans/{plan_id}/replan`   | 主动触发重排 | 原 `reblance` 改名，必须检查冷却        |
| GET  | `/api/v1/plans/{plan_id}/insights` | 数据洞察     | 原 `analyze` 可改名，也可保留 `analyze` |

### 建议新增

| 方法  | 路径                                         | 说明                                         |
| :---- | :------------------------------------------- | :------------------------------------------- |
| GET   | `/api/v1/users/me`                           | 当前用户信息                                 |
| GET   | `/api/v1/plans`                              | 当前用户的计划列表                           |
| GET   | `/api/v1/plans/{plan_id}`                    | 计划详情（含任务、子标准、认知标签、缓冲）   |
| GET   | `/api/v1/plans/{plan_id}/feedback`           | 反馈历史                                     |
| GET   | `/api/v1/plans/{plan_id}/replan/eligibility` | 主动重排资格：能否重排、下次可重排时间、原因 |
| PATCH | `/api/v1/plans/{plan_id}/tasks/{task_id}`    | 可选：勾选任务，若反馈接口已覆盖可不要       |