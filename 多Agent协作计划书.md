# 多 Agent 协作计划书 v0.2：课本教练（答疑）× 教案 Agent —— 两个独立 Agent

> 日期 2026-09-06｜性质：立项/施工计划（编码暂停中）
> 基线：课本教练单 Agent 已交付（S1~S9 全绿；UI 现为唯一入口 http://127.0.0.1:5174 web_server，Gradio 版已归档 legacy/）

---

## 0. 独立性硬性声明（本计划最高优先级约束，施工与验收均以此为准）

> **Agent A（课本教练）与 Agent B（教案 Agent）必须是两个相互独立、各自完整的 Agent，而不是一个模型里拼接的两段提示词，也不是同一个 Agent 的两个"子功能"。**

独立性的具体含义与判据：

| # | 独立维度 | 要求（验收判据） |
|---|---|---|
| 1 | 独立实体与身份 | 两个 Agent 各自拥有独立的 Agent 定义：独立角色/系统提示词、独立职责、独立输出契约（AnswerRecord / PlanRecord），互不混用 |
| 2 | 独立运行入口 | 每个 Agent 可独立启动、独立运行：A 不启动 B 也能完整答疑；B 不启动 A 也能完整出教案。代码上各自独立模块 + 各自命令行入口 |
| 3 | 独立知识/状态 | 各自独立维护自己的对话上下文与内部状态；除共享只读的教材向量库与通用工具外，不共享可变内部状态 |
| 4 | 独立故障隔离 | 任一 Agent 异常/不可用时，另一个 Agent 仍能独立完成本职工作；编排层不能因为 A 挂了导致 B 不可用 |
| 5 | 松耦合通信 | 两个 Agent 之间只通过明确定义的契约交换消息（结构化的输入/输出 JSON），不读写对方内部，不共用对方提示词 |
| 6 | 可独立替换/扩展 | 每个 Agent 可被独立升级、替换为其他实现（如换模型、换检索），不影响另一个 Agent |

一句话红线：协作 ≠ 合并。可以共用一个向量库和编排层，但 Agent A 与 Agent B 永远是两个能单独跑的 Agent。

## 0.5 新增需求：教案模板认定 + 模板化生成（以模板为主）

定位：Agent B 的扩展职责（独立于 Agent A）。老师可先"认定"一个教案模板，之后 B 生成教案时以该模板的板块结构与顺序为主。

**模板认定是什么**
- 输入（以 Word .docx 为例子）：老师上传一份模板 docx，如《教案模板.docx》或过往优秀教案，内含标题行（一、教学目标…）、正文段落、以及表格（如 教学环节/教师活动/学生活动/设计意图 四列表）等。也兼容直接粘贴文本或结构说明。
- 认定动作（docx 解析路径）：B 用 python-docx 读取 docx → 按标题层级（Heading 1/2、"一、二、"编号行、加粗段）识别板块与顺序；表格整体抽取为 board/表格类板块；无样式的纯文本段落并入前序板块 → 产出结构化 TemplateSpec{template_id, name, blocks:[{type, order, note}]} → 把解析出的板块结构回读给老师确认；"认定"以老师确认为准（老师可让 B 增删改板块后再次认定）；
- 存档：模板存 content/templates/（docx 原件 + 解析出的 TemplateSpec.json 一并存；内置默认模板 1 份），支持多套并存与切换。

**模板化生成（以模板为主）**
- 生成时携带 TemplateSpec：B 按模板 blocks 的顺序逐一产出内容；模板没有的板块不硬加，板块内素材不足时明说待补；
- PlanRecord 扩展字段：template_id、template_name、blocks（对齐模板）；
- 未认定任何模板时，回退到默认完整课时模板（默认模板本身也是可被替换的）。

**UI**：教案页增加「模板」区——认定模板 / 选择当前模板 / 展示当前模板结构。

**验收新增（并入 M1/M4）**：认定一份老师模板（例如含"作业布置"板块）→ 其后生成 3 份教案，板块名称与顺序与模板一致；模板未含的板块（如无"板书设计"）不会自动出现。

---

## 1. 目标

以两个独立 Agent 组成教学双 Agent：学生向 A 提问获得教材依据答疑；老师向 B 报"知识点 + 教学问题/目标"获得教材依据的教案；二者通过编排层协作，形成"学生问（A 答）→ 老师备课（B 出教案，引用同源课本 + 承接 A 的答法学情）"的闭环，但 A、B 各自可单独对外服务。

## 2. 两个独立 Agent 定义

### Agent A —— 课本教练（Coach，答疑 Agent）【已交付】
- 身份：面向高中生的教材答疑 Agent（prompts.SYSTEM_PROMPT）
- 独立入口：generate.ask(question) -> AnswerRecord；CLI：python src/edu_agent/generate.py "问题"
- 输出契约：AnswerRecord{answer_md, citations, coverage, confidence}
- 依赖（只读共享）：Chroma 教材库、DeepSeek LLM、Ollama bge-m3、retrieve（主节优先）

### Agent B —— 教案 Agent（Planner，备课 Agent）【本计划新建】
- 身份：面向老师的备课 Agent（prompts.PLAN_SYSTEM，独立于 A 的角色与提示词）
- 独立入口：planner.make_plan(knowledge_point, goal) -> PlanRecord；CLI：python src/edu_agent/planner.py "知识点" "教学问题/目标"
- 输出契约：PlanRecord{title, objectives, key_points, flow_steps(phase/minutes/content), mistakes, citations}；模板化时扩展 template_id/template_name/blocks
- 扩展职责：支持**教案模板认定**（见 §0.5）：解析老师模板 → TemplateSpec → 存档 content/templates/ → 生成以当前模板为主
- 依赖（只读共享）：同一个 Chroma 教材库、DeepSeek LLM、retrieve（kinds 含 concept+section）；不得复用 A 的提示词与输出类型

### 两 Agent 各自独立但可协作的部分
- 共享（只读、无耦合）：教材向量库、embedding/LLM 通道、页码引用坐标系（保证两 Agent 的引用能对上）
- 协作通道（契约级）：编排层把 A 的 AnswerRecord 作为 B 的"学情/前情"输入之一（P1），B 自己决定怎么用

## 3. 架构：独立 Agent + 编排层（LangGraph 单进程编排，A/B 仍为独立 Agent）

用户输入 -> Orchestrator 编排层（LangGraph StateGraph，只做路由/上下文传递，不实现答疑也不实现备课）
             -> Agent A 课本教练（独立）
             -> Agent B 教案 Agent（独立）
两个独立 Agent：各自 system prompt / 职责 / 契约；各自可独立运行（CLI/服务）；只读共享教材库
共享底座：Chroma(151 块) + 主节优先检索 / DeepSeek / bge-m3 / plainify
（P1）A 的 AnswerRecord 经编排层作为 B 的输入上下文 -> B 独立加工出教案

要点：
1. 编排层（LangGraph）只负责：意图路由、上下文传递、结果组装——不内置任何一方的提示词与逻辑；
2. A、B 保持第 0 节全部独立性判据：每个 Agent 单测时直接调用其独立入口即可，与编排层无关；
3. P1 协作 = 编排层把 A 的输出（含引用页码）转交 B，B 作为独立 Agent 决定是否采纳——B 缺失时编排层直接回 A 的结果，A 缺失时 B 也可独立出教案（不依赖 A 的答案）。

### 3.3 官方模式对照与选型结论（2026-09-07 定案，依据 hermes《LangGraph多Agent协作-官方模式学习与落地建议.md》）

| 环节 | 官方模式 | 结论 |
|---|---|---|
| 整体编排 | Router（无状态规则路由） | 采用：graph.py 已是官方 Router 干净实现；类别清晰 + 规则分类够用（省一次 LLM 路由调用） |
| 双入口 | 显式双 Tab 指定 mode | 采用：官方明确 Router 自动多轮横跳会造成口径不连贯，双 Tab 让 A/B 各对各自用户 |
| A到B协作(P1) | Stateful Router + 上下文工程 | 采用：State 增加 coach_summary；进 B 前把 A 的 AnswerRecord 压成学情摘要（问题+要点+页码）注入 goal；B 无摘要照常独立出教案（独立性验收点） |
| 模板认定(M0) | Skills 模式本地版 | 采用：template_spec 定位为 B 的教案技能，按需加载 blocks 结构 |
| 排除 | Subagents/supervisor、Handoffs | 排除：前者中央集权违反独立性；后者用于控制权移交，A/B 是两个入口两类用户用不上 |
| 铁律 | 官方上下文工程 | 交接只传摘要不传全史；返回用户前最后一条须 AIMessage；A 未来多轮用 tool wrapper + checkpointer，不手搓历史 |

---

## 4. 独立 Agent 的代码与部署边界（草案）

| 层 | 归属 | 说明 |
|---|---|---|
| edu_agent/generate.py + prompts(SYSTEM) | Agent A 本体 | 已交付，独立可跑 |
| edu_agent/planner.py + prompts(PLAN_*) | Agent B 本体 | 草稿已建（未接线），独立可跑（CLI） |
| edu_agent/retrieve.py / ollama_embeddings.py / config.py | 共享只读底座 | 两 Agent 公共依赖，非 Agent 本体 |
| edu_agent/graph.py | 编排层（新） | LangGraph StateGraph：route 到 A 或 B；只传消息 |
| web_server.py「答疑/教案/总指挥」网关 | 接入层 | 页面背后各自只调自己 Agent 的独立入口（旧 Gradio api.py 已退役归档 legacy/api_gradio.py，接入层统一为 5174 网关） |
| （P2 可选）A、B 各自独立 FastAPI /v1/ask 与 /v1/plan | 部署边界 | 满足可独立部署；编排层退化为网关 |

## 5. 分步施工与验收（计划，未开工；每一步都验证独立性）

| 里程碑 | 做什么 | 验收（含独立性判据） |
|---|---|---|
| M0 | 模板认定：读 Word .docx -> 解析板块 -> TemplateSpec -> 存档 content/templates/ | 用一份《教案模板.docx》样例走通认定并回读确认；内置默认模板可用 |
| M1 | B 单测：不启动 A，planner.make_plan 3 样例独立出教案（默认模板 + 已认定模板各验） | B 独立完成：JSON 合法、环节+页码引用、无乱码、回应学情；用认定模板时板块与顺序一致 |
| M2 | 编排层 graph.py：route -> 调 A 或 B 的独立入口 | A 问题进 A、教案话术进 B；关闭 B 时 A 仍正常（故障隔离） |
| M3 | UI「教案」页：只调 B 独立入口 | 教案页与答疑页互不影响，任一页异常不影响另一页（解耦） |
| M4 | 打磨 3 份样例教案 + 学情抽检（按已认定模板生成） | 引用页码真、学情问题有对应环节、板块对齐认定模板（§0.5 验收） |
| M5(P1 可选) | 编排层把 A 的 AnswerRecord 传给 B（协作增强） | B 收到前情后教案更贴学生问题；不给前情时 B 照常出教案 |
| M6(可选) | 教案落盘 content/plans/ | 复用不覆盖 |

## 6. 资源与成本
- 全复用现有（langgraph 已装）；M0 新增依赖 python-docx（解析 Word）；新增仅 1~2 天人力（M0~M4）+ DeepSeek 调用量（教案 1 次/份）。

## 7. 风险与对策
| 风险 | 对策 |
|---|---|
| 引用页码张冠李戴 | 复用引用规整机制 + M1/M4 抽检 |
| 检索缺失（如 4.2 表格污染） | B 明说该节教材细讲未收录，教案标注补材料 |
| 生成慢（输入敏感） | 沿用瘦身（片段 ≤800 字、top≤4；教案限 600~1200 字） |
| 独立退化成一段代码两提示词 | 第 0 节判据逐条进验收：M1/M2/M3 必须各自断网式独立跑一遍 |
| LangGraph API 变动 | 只使 StateGraph/条件边最小面 |

## 8. 待拍板
1. 教案粒度：课时教案（默认 40/45 分钟）还是知识点卡片？
2. 可选参数：课时分钟、学生水平、板书设计，要不要？
3. P1「A 答完 -> B 承接」是否进首版演示？
4. 教案是否落盘 content/plans/？
5. P2 是否需要把 A、B 各自拆成独立 FastAPI 服务（部署级独立），还是演示期同进程两个独立 Agent 即可？
6. 模板认定入口形态（建议以 Word .docx 为默认例子）：老师直接上传 .docx 模板/样例教案；是否同时保留粘贴文本与引导式问答两种入口？
7. 默认模板定为一套完整课时模板（教学目标-重难点-教学过程-板书-作业）是否可行？

---
*本计划书待确认后转施工。现有草稿：planner.py（Agent B 独立入口雏形）、prompts PLAN_*（未接线）；Agent A 已交付。*
