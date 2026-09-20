# DAMN 移动端交互设计调研报告

> 产品结论均附来源；标「推断」的为本文推导；无法取回正文的页面标 **未能核实**。

## 0. 三条贯穿全案的硬约束

| 约束 | 数值 | 来源 |
| --- | --- | --- |
| 响应时间三阈值 | 0.1s 瞬时 / 1.0s 思路不中断 / **10s 注意力上限**。超约 10s 必须要 percent-done 指示器 + **明确的"可中断"入口**；spinner 只适合 2–10s | [NN/g](https://www.nngroup.com/articles/response-times-3-important-limits/) · [进度指示器](https://www.nngroup.com/articles/progress-indicators/) |
| 触控目标 | WCAG 2.2 SC 2.5.8（AA）**24×24 CSS px**。与 iOS 44pt 是两套标准，勿混用 | [W3C](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) |
| AI 能力呈现 | LangChain **官方**「Graph execution cards」范式：每个 LangGraph 节点一张卡，显示 idle/streaming/complete、流式内容，顶部全局步骤条，完成节点自动折叠，**错误按节点就地显示**，条件跳过的节点置灰或隐藏 | [LangChain Docs](https://docs.langchain.com/oss/javascript/langgraph/frontend/graph-execution) |

> ⚠️ **DAMN 直接受益点（推断）**：`AGENTS.md` 要求 SSE stage 名 = 节点名（`goal_analysis` 等 6 个 + `completed`），正是这个官方范式的输入。**不要自造等待态 UI，直接把 stage 事件映射成步骤条**。

**可借鉴 vs 需谨慎（全案）**：可借鉴——用连续色阶而非卡通表达情绪（Apple/Amie）、时长前置为一级字段（Sunsama/Motion/Tiimo）、把 SSE 阶段直接映射成步骤条、Oura 式归因句式 + 公示门槛、Duolingo 式"给弹性反而提升留存"（Streak Freeze 使 DAU +0.38%）、触控目标 ≥24×24 CSS px 且主按钮 44pt+。需谨慎——不要用动物吉祥物式"幼稚化"温暖；不要把推荐做成信息密集看板（Rise 的教训是"改动不可见"）；**不要用骨架屏当默认等待态**；不做 WHOOP 式"休闲化回顾"、不用 Beeminder 式内疚话术；不用红色/欠账标记惩罚"今天先不做"；**绝不伪造 AI 进度文案**。

---

## 1. 状态自评 / 心情签到页

| 产品 | 流程 / 步数 | 量表形式 | 来源 |
| --- | --- | --- | --- |
| **Apple State of Mind** | 日常核心 **3 个决策页**（滑块 → 形容词 → 影响来源） | 连续 valence 滑块（−1…+1，紫→蓝→橙）+ 形容词单选 + 影响来源多选 | [HKStateOfMind](https://developer.apple.com/documentation/healthkit/hkstateofmind) · [MacRumors](https://www.macrumors.com/how-to/track-mood-with-apple-health/) |
| **Daylio** | 官方口径「**两次点击**」完成记录 | 默认 **5 个基础心情** emoji；官方建议"先从 5 个心情开始，流程才简单快速" | [Daylio FAQ](https://daylio.net/faq/docs/daylio-faq/tutorials/create-and-manage-moods/) |
| **How We Feel** | **5 步** | 二维四象限情绪气泡墙：颜色=类别，位置=强度，每词有独立形状 | [Yale](https://medicine.yale.edu/psychiatry/step/news-article/the-how-we-feel-app-helping-emotions-work-for-us-not-against-us/) · [Pratt 设计批评](https://ixd.prattsi.org/2026/09/design-critique-how-we-feel-app-ios/) |
| **Structured** | 不是心情页，是**能量预算**：给任务选能量等级 → 时间轴顶部看当日能量条 | 6 档能量等级，按任务时长每 30 分钟折算 Energy Points | [官方帮助](https://help.structured.app/en/articles/998530) |
| **Bearable / Finch** | **未能核实**（JS 渲染 / 帮助中心不可访问） | Bearable 可确认存在 0–10 类症状量表 | [Bearable](https://bearable.app/support/common-questions/change-or-customise-symptom-scales-e-g-0-to-10/) |

**量表形式的研究证据（本节最反直觉）**：5 点表情脸 / Likert 认知负担最低、临床最成熟（Wong-Baker FACES 面向 3 岁以上），但 CES-D 8 被试内对比显示它与滑块在信度/效度/因子结构上**结果相似**。**VAS 滑块**粒度细：14 天 EMA 对照中其个体内均值与自相关更高、偏度更低，与精神病理效标相关"**高得多**"，而**缺失率与作答时长并无可靠差异**——作者建议捕捉情绪时优先 VAS。**Emoji 网格**序性可验证：5 个 emoji 两两比较中 **95% 患者给出同一次序**，与 LASA 相关 r=0.70–0.81。[Zhang 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12924885/) · [Haslbeck 2025](https://doi.org/10.3758/s13428-025-02706-2) · [Thompson 2025](https://pubmed.ncbi.nlm.nih.gov/39772639/)

**负担感——证据不支持"题越少越好"的强假设**：168 项研究元分析依从率 **81.9%**，非临床中位 **7 天 / 5 次提示/天 / 8 题/次**，且"未发现负担类方案特征与依从性之间有令人信服的关系"（[Williams 2021](https://pubmed.ncbi.nlm.nih.gov/33656451/)）；N=411 因子实验中题量 15 vs 25、每天 2 次 vs 4 次、**滑块 vs Likert 全部无显著主效应亦无交互**，而"**喜欢该 App**"与依从率显著正相关（[Businelle 2024](https://pubmed.ncbi.nlm.nih.gov/39133915/)）。**推断**：决定留存的是"喜不喜欢这个界面"与提示时机，不是题数；但实践高度收敛在 **2–3 个决策页**。

**"有温度但不幼稚"（可验证做法：用颜色而非卡通）**：Amie 官方设计语言要求"纯白底 + 近黑文字 + 品牌粉 `#f6a6a6` 作为**每屏只用一次**的情感点缀"，并"用表面色而非文字色表达状态"（[Amie 设计语言](https://raw.githubusercontent.com/educlopez/design-bites/main/design-mds/amie.so/DESIGN.md)）。

> **DAMN 应该怎么做**：做**单屏 3 步**（精力/压力用连续滑块 → 心情用 5 项 emoji → 可选一句"什么影响了它"），允许一键跳过直接提交，情绪温度用连续色阶而非卡通表情。

---

## 2. 「现在做什么」推荐卡片页（灵魂页）

| 产品 | "现在做什么"的呈现 | 视觉要点 | 来源 |
| --- | --- | --- | --- |
| **Sunsama** | **无单张推荐卡**。"带时间估算的有序清单"+ **Focus Mode**：官方定义为"只显示你此刻正在做的那一个任务的最小化视图"，完成后焦点**自动移到下一个** | `planned time` 是任务**一级字段**；顶部**工作量计数器**（接近阈值变黄、超额变红）；Focus Bar 用 play/pause/check 三键 | [Daily Task List](https://www.sunsama.com/blog/why-we-built-it-daily-task-list) · [Focus Mode](https://help.sunsama.com/docs/usage-guides/focus-mode/) |
| **Tiimo** | 可视时间线 + 专注页（"把分钟变成可视倒计时"）；Widget / Dynamic Island 承担"抬眼即知现在" | 专注页含**标题 + 倒计时 + 进度环 + 子步骤**；官方样例 "42 minutes left" | [Focus Timer](https://www.tiimoapp.com/product/focus) · [Widgets](https://www.tiimoapp.com/product/widgets-live-activities) |
| **Motion** | **AI Agenda** 列表（非单卡），官方称"让你始终知道**接下来该专注什么**" | 每任务显示 duration 与 ETA；**理由靠图标**（❗过期、优先级符号） | [AI Agenda](https://www.usemotion.com/help/time-management/ai-agenda.md) |
| **Reclaim.ai** | 决策落在日历事件上；"开始"是**显式动作** | 优先级 P1–P4；冲突重排约 15 秒内；排不下时保留事件加 ⚠️ | [自动排程](https://help.reclaim.ai/en/articles/6207587-how-reclaim-manages-your-schedule-automatically) |
| **Amie / Structured** | 未见官方"单张现在卡"说明 | **未能核实** | [amie.so](https://amie.so/) · [structured.app](https://structured.app/visual-planning) |
| **Rise** | **产品已于 2025-03-31 关停** | 不存在 | [risecalendar.com](https://risecalendar.com/) |
| **Session**（番茄钟） | 开工前需 **"State your focus"** 声明本次目标 | 旋钮调时长；结束追问"你学到了什么" | [stayinsession.com](https://www.stayinsession.com/) |

> 🔴 **最强证据（Rise 停运复盘）**：他们做了自动重排，但用户"**并不真的感觉到 Rise 有正面影响**"，并把所有日历问题归责于它（即使不是它造成的）。补救是"减少改动次数、**在事件里写明我们不会再移动它**、对'发生了什么'给出多得多的可见性"、以及"**预览这些移动**"。仍没救活。→ **AI 决策的"正确"不等于被感知；"为什么这么排 / 这次改了什么 / 怎么撤销"必须是一等界面。**

**AI 生成等待态**：**阶段步骤条**是多秒级 AI 生成的首选——NN/g 指出算不出百分比时"仍可提供绝对工作量形式的进度反馈"。**流式文字**适合产物为文字且首 token 延迟低的场景，但 Vercel 官方记录了一个通用坑：status 在**连接建立时就变 streaming**（含 metadata 不含 token），于是"显示思考中但几秒无字"，修复是仅当 `parts.length === 0` 才显示 loader（[AI SDK](https://ai-sdk.dev/v5/docs/troubleshooting/streaming-status-delay)）。**骨架屏不要当默认**：136 人对照实验中它**全指标最差**——"加载很快"认同率 59%（spinner 74%、空白 66%）（[Viget](https://www.viget.com/articles/a-bone-to-pick-with-skeleton-screens)）。

> **DAMN 应该怎么做**：一屏一卡，**任务名作 H1（唯一最大字号）、预计时长作紧邻副标签**（Sunsama/Tiimo 都把时长前置），正中一个高权重 ≥44pt"开始"按钮，进度环只在**真有剩余量**时出现；生成态**用 6 阶段步骤条**（直接消费 SSE stage），完成态自动切下一张，**每张卡带一行"为什么是这件事" + 跳过入口**。

---

## 3. 任务列表 + 打卡页

- **范式差异（推断）**：Things 3 / Todoist / TickTick 重**信息密度与分类**；Streaks / Loop / Habitica 重**单一动作 + 视觉连续性**。DAMN 是"AI 已排好序的执行清单"，**弱化分类，强化一键完成**。
- **列表密度**：移动端 padding 从 p-6 收到 p-3 可使可见条数**翻倍**（[dot-skills](https://raw.githubusercontent.com/pproenca/dot-skills/refs/heads/master/skills/.experimental/tailwind-responsive-ui/references/data-list-density-mobile.md)）→ **推断**：一屏 **6–8 条**，每条只留「标题 + 时长 + 完成控件」。
- **"跳过"措辞有语料数据**：74 个 App 的软拒绝按钮统计 **"Not Now" 18 个**，远超 "Skip"（8）与 "Maybe Later"（5）——"Not Now" 表达**临时**而非永久放弃（[Lazyweb](https://www.lazyweb.com/research/notification-decline-cta-not-now-vs-skip)）→ **推断**：写"**今天先不做**"，不显示欠账标记。
- **反面教材**：Beeminder 官方都在警告不要把"因内疚而做"的 *Should goals* 纳入系统，并建议把惩罚框定为"税"而非惩罚（[Beeminder](https://blog.beeminder.com/nuclear)）。动效方面**未能核实**"完成动效提升留存"的量化研究；可核实的是 Duolingo **连胜动画**使新用户 7 日后仍使用概率 **+1.7%**（[Duolingo](https://blog.duolingo.com/how-duolingo-streak-builds-habit/)）。

> **DAMN 应该怎么做**：一屏 6–8 条，每条只有"标题 + 时长 + 圆形完成键"；完成后行内微动效 + 0.3s 内消失上移，**"今天先不做"与"完成"视觉权重同级、无红色、无欠账计数**。

---

## 4. 周反馈 → 调整页

| 产品 | 报告内容 | 图表 | 话术风格 | 来源 |
| --- | --- | --- | --- | --- |
| **Apple Fitness / Health** | 官方确认为 activity history / trends / awards | 形态**未能核实**；HIG `Charts` 要求**避免主观词**（rapidly/gradually），给具体数值让用户自行解读 | 客观数值 | [HIG Charts](https://developer.apple.com/design/human-interface-guidelines/charts) |
| **Oura** | 周/月报 = 平均准备度、睡眠、活动分 + 构成因素趋势 | "趋势图"（类型**未能核实**） | **归因假设式**："睡眠分数下降可能表明深夜锻炼、小睡或饮食影响了睡眠质量"；并**公示门槛**（需累计 ≥2 周） | [Oura 帮助中心](https://support.ouraring.com/hc/zh-cn/articles/360046061373) |
| **Strava** | Year in Sport = App 内**逐屏故事卡**，每屏可单独分享；公示门槛（≥3 条活动、限时开放） | **未能核实** | 庆祝式 + 社交比较 | [Strava Help](https://support.strava.com/en-us/articles/15401959-your-year-in-sport) |
| **Duolingo** | 连胜、成就、Year-in-Review 卡片 | 连胜火焰 + 7 列日历格 | 损失厌恶 + **主动给 slack**：官方承认断连胜会 demotivating、"怕断"会让人不敢开始，故引入 Streak Freeze；加弹性反使 DAU **+0.38%** | [Duolingo](https://blog.duolingo.com/how-duolingo-streak-builds-habit/) |
| **WHOOP** | MPA 被 Month in Review 取代；图表**未能核实**（403） | — | 反面案例：用户批评新报告"casual content"、洞察不如 MPA → **"休闲化"会削弱信任** | [WHOOP 社区帖](https://www.community.whoop.com/t/new-month-in-review-is-a-huge-disappointment/9035/11) |

**移动端图表选型**（[Datawrapper](https://www.datawrapper.de/blog/chart-types-guide)）：**横向条形图最安全**——小屏上纵向生长、标签不重叠；纵向柱形图在约 30 根柱子挤到手机宽度时标签即重叠；折线图是时间趋势默认首选；饼图/环形图只适合**单一**部分-整体（"3% 的差异在条形图里一目了然，在环形图里几乎看不见"）；热力图与散点被官方称为"复杂""读者易 overwhelmed"。**推断**：进度环 + 中心数字用于单一 "8 / 12" 可接受。

> **DAMN 应该怎么做**：用 **Oura 式归因句式 + 一个大数字对比**——页首直接写「上周完成 **8/12**，所以这周给你排 **8** 个」（大数字 + 横向条形对比两周），下方一句"如果这周压力感还是偏高，我会再减"，**底部放"我想恢复原计划"的回退入口**（Rise 教训：可撤销是一等界面）。

---

## 5. 目标输入页

| 做法 | 优点 | 缺点 | 来源 |
| --- | --- | --- | --- |
| 单一大输入框 + placeholder + 示例 chips | 门槛最低 | 八个头部 AI 产品全是"空白框 + 一句话 + **一敲字就消失**的 chips"，被批评为"让用户自己发明价值主张"——**signifier 应当持久** | [Victorino 分析](https://victorinollc.com/thinking/ai-empty-state-ux-governance-collapse)（二手，已披露 LLM 辅助撰写） |
| 多步 stepper | NN/g：适合**新手或不常做的流程**；字段更少 → 不易被吓退、错误更少 | 交互成本更高；**不能优雅中断**；**超过 2 层披露通常可用性差**；必须显示步骤清单并高亮当前步 | [NN/g: Wizards](https://www.nngroup.com/articles/wizards/) · [Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/) |
| 单页表单 | 字段少时最快 | 字段多时"用户会高估工作量"；NN/g 表单十条明确**避免 placeholder 文案**（会消失、易被误认为已填值） | [NN/g: Forms](https://www.nngroup.com/articles/web-form-design/) |
| 阶段化 AI 状态文案 | 比"什么都可能意味着的 spinner"安心得多 | ⚠️「**伪造的阶段标签**（什么都没分析却说 "Analyzing…"）一旦被看穿是表演，就会侵蚀信任」 | [Frontend Patterns](https://frontendpatterns.dev/thinking-indicator) |

**推断**：DAMN 输入页只有一个自由文本字段，属"字段极少"，**stepper 的收益远小于其"不能优雅中断"的代价** → 应选**一页搞定 + 一次追问**。

> **DAMN 应该怎么做**：一页一个大输入框，**用持久 label 而非纯 placeholder**（"你想达成什么？"），下方放 3–4 个**不会因输入而消失**的示例 chip（"三个月内跑完半马"），提交后立刻在原位放 thinking indicator，**只在真实到达该阶段时**才点亮步骤文案，**绝不伪造进度**。
