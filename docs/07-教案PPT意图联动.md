# 教案 / PPT 意图联动（v1.9.0 · 一期）

老师问到「教案 / 课件 / PPT」时，对话里会多出一张**下一步选项卡**，给两条路：

- **① 生成教案模板** —— 让教案 Agent 把这节课**归纳成板块骨架**（含每个板块的填写提示与表格表头），
  存进模板库，以后任何一节课都能套用；
- **② 按模板生成** —— 从模板库里**选一个模板**（多个模板时给下拉），教案 Agent 严格按它的板块名称与顺序产出教案。

> 规划与取舍见 `docs/06-教案PPT意图联动计划书.md`；模板的导入与编辑见 `docs/05-教案模板导入与编辑.md`。
> 本文只讲**一期已落地**的部分。

## 1. 老师怎么用

问一句涉及教案的话即可，例如：

- 「帮我备一节 3.3 幂函数的课，要课件」
- 「这节函数的教学设计怎么做」
- 或先让教案 Agent 出一份教案，再问「给我整一份 PPT」

回答下方会出现「下一步」卡片，两个按钮：

| 按钮 | 点了会发生什么 | 耗时 |
|---|---|---|
| **① 生成教案模板** | 教案 Agent 归纳出板块骨架 → 提示条变成「已生成《X》：9 板块 · 3 表　**去教案中心编辑**」 | 约 10–20 秒 |
| **② 按模板生成** | 按下拉里选中的模板重新生成教案（等于 `preset=B` + `template_id=...`） | 与普通教案生成相同 |

- 模板多于 1 个时，② 旁边出现**下拉**，列出每个模板的「板块数」与是否「可编辑」（`rich`）；
- 少于 2 个时只显示模板名，不显示下拉；
- **选择会被记住**（`localStorage: edu_chat_tpl`），下次默认还是它；
- ① 生成完可以直接点「去教案中心编辑」跳到模板编辑器，改完「保存为模板」即可复用。

## 2. 触发规则：两类信号，任一命中

判定在 `routing.involves_plan_topic(text, hits)`，返回 `(是否涉及, 原因)`：

| 原因 | 信号 | 例子 |
|---|---|---|
| `intent` | 问题里有 教案 / 备课 / 教学设计 / 课堂设计 / 课件 / **PPT** / 幻灯片 / 演示文稿 / slides / 说课 / 讲稿 / 导学案 / 教案模板 | 「这节教案怎么写」 |
| `retrieval` | **检索命中的片段**的来源名、标题、章节或正文开头里有上述词 | 老师上传过课件 PDF，按 `corpus=pdf:` 检索命中 |
| `plan_mode` | 派单结果是 **B（教案 Agent）**，无需信号，恒给 | 「帮我备一节 3.3 幂函数的课」 |

**零打扰**是硬要求：普通答疑（问一道题、问概念）**不出现**这张卡片。
`tests/test_plan_link.py` 里专门有一条「普通答疑不产生 options 事件」的回归。

### 顺带修掉的两个派单漏判（`routing.PLAN_HINTS`）

- 「要 **ppt**」以前判成 A（词表里只有「课件」）；
- 口语「帮我**备一节** 3.3 幂函数的课」以前判成 A。

现已补齐：`ppt`、`幻灯片`、`演示文稿`、`slides`、`课件制作`、`说课`、`备一节`、`备一课`、`备这节课`。

## 3. 选项①「生成教案模板」是怎么产出的

`planner.make_template(topic, goal)`：一次 LLM 调用 → 结构化 JSON → 转成可编辑的富模板。
产出物满足「**骨架 + 填写提示 + 表头**」三要素（一期锁定的口径）：

- 板块骨架：只给板块名与顺序，**不写具体教学内容**；
- 每个板块下有一句**填写提示**（说明这个板块该填什么、有什么要求）；
- 表格类板块（教学过程、板书设计等）**带上表头**（如 环节 / 教师活动 / 学生活动 / 设计意图）；
- 存进 `content/templates/<id>.json`（`spec_version: 2`，`rich: true`），走 `template_rich.save_rich()`，
  **和「导入 .docx / 全量编辑」是同一套模型**，所以生成完能直接在教案中心改到每一段、每一格。

接口：`POST /api/plan/template`

```jsonc
// 请求：topic 留空时会话里最近一份教案的课题兜底（_last_plan_topic）
{"topic": "3.3 幂函数", "goal": "", "session_id": "...", "save": true, "set_current": false}
// 响应
{"ok": true, "template_id": "新授课通用教案模板", "name": "新授课通用教案模板",
 "stats": {"blocks": 9, "tables": 3}, "skeleton": "# …（markdown 骨架）", "path": "…json"}
```

实测：「帮我备一节 3.3 幂函数的课，要课件」→ 点① → **14 秒**产出《新授课通用教案模板》，
**9 板块 / 3 个表格板块**，带填写提示与表头，落库为可编辑模板。

> 一期不自动设为「当前模板」（`set_current: false`）——避免悄悄改掉 Agent B 的默认模板。
> 需要的话在教案中心点一下「保存为模板」即可。

## 4. 选项②「按模板生成」：修掉一个写死的 `default`

前端原先发 `/api/chat` 时 **`template_id` 恒为 `'default'`**，所以「选模板」这件事此前根本传不到后端。
现在：

- 新增 `CHAT_TPL` 变量 + `sendText(val, {preset, templateId})`；
- ② 按钮把下拉里的值传进去，并 `planOptsRemember()` 记住；
- 后端沿用既有链路：`/api/chat` → `_stream_planner` → `planner.make_plan(template=req.template_id)`，
  **后端一行没改**（这正是计划书 §5 说的「② 走既有管道」）。

jsdom 真 DOM 回归实测点击 ② 之后的请求体：

```
POST /api/chat  {"text":"帮我备一节 3.3 幂函数的课","preset":"B","template_id":"新授课通用教案模板"}
```

## 5. 提示词的两处收口

| 位置 | 改了什么 | 为什么 |
|---|---|---|
| `prompts.SYSTEM_PROMPT` 第 8 条 | A（课本教练）**不越界写教案**，改为引导用户点这两个按钮 | 以前老师问「教案怎么写」会得到一份半成品教案，和 B 的产出打架 |
| `prompts.PLAN_TEMPLATE_GUARD` | 骨架约束从 planner 内联**提到 prompts 统一维护**，并补第 3 条「**本板块教材依据不足，请补充**」 | 原先只有「不得增删板块」，模型碰到教材没覆盖的板块会硬编内容 |

顺带修掉 `prompts.JSON_INSTRUCTION` 里 `\subseteq` / `\frac` / `\log` 的无效转义（历史遗留 `SyntaxWarning`），
行为不变。

## 6. 事件协议（向后兼容）

生成层（`generate.ask_stream`）在 `done` 事件里带一个信号字段：

```jsonc
{"t":"done", ..., "plan_options": {"suggest": true, "reason": "intent"}}  // 不涉及教案时为 null
```

`web_server._with_plan_options()` 把 Agent 流**原样透传**，收尾时按需补一个事件：

```jsonc
{"t":"options", "kind":"plan", "reason":"plan_mode|intent|retrieval", "topic":"3.3 幂函数",
 "options":[
   {"id":"gen_template","label":"生成教案模板","hint":"…"},
   {"id":"use_template","label":"按模板生成","hint":"…",
    "templates":[{"template_id":"…","name":"…","blocks":9,"rich":true}], "current":"…"}
 ]}
```

- 事件类型集合仍是 `{session,status,d,delta,done,error,options}`——**老前端会忽略不认识的 `t`**，所以是加法；
- A / S 派单只有 `suggest=true` 才补；B 恒补（`reason=plan_mode`）。

## 7. 一期边界（还没做的）

一期只覆盖「**给选项 + 两个选项真的能用**」，下面这些属于二期 / 三期：

- **按板块填充已有教案**（`plan_sync`，已随「会话教案同步」撤回，可 `git cherry-pick reverted/plan-sync-20260912` 取回）——
  即「我已经有一份教案正文，按模板把内容灌进对应板块」；一期是**重新生成**，不是填充。
- **对话里的导出条**（Word / PPT / HTML / 预览 + 位置 + 下载）——目前导出在教案中心，
  对话里只能点「去教案中心编辑」再导出。
- 空板块黄条提示、生成前预检、导出前置校验、自动弹选项的设置开关。

## 8. 排错

| 现象 | 原因 / 处理 |
|---|---|
| 涉及教案但**没有**卡片 | 派单可能是 A 且检索也没命中。看响应流里有没有 `options` 事件；`routing.PLAN_HINTS` / `TOPIC_HINTS` 是唯一改动点 |
| 普通答疑却**出现**了卡片 | 检索片段里含「教案/课件」等词（`reason=retrieval`）。卡片标题会写明原因 |
| 点① 报「缺少课题」 | 会话里没有教案回答、也没传 `topic`；先问一句或直接传课题 |
| 点① 报「模型没有产出板块」 | 模型这一轮 JSON 没解析出来，再点一次即可 |
| 点② 出来的教案跟模板对不上 | 确认下拉里选的模板；模板本身的板块名在教案中心可见（`content/templates/<id>.json`） |

## 9. 测试

`tests/test_plan_link.py`（18 例，全离线）：

- 派单补词（ppt / 备一节…）、`involves_plan_topic` 的 intent / retrieval / 否三条路径；
- `plan_options` 只在涉及教案时置位；普通答疑为 `None`；
- `options` 事件：B 恒给、A 有信号才给、模板清单与 `current` 形状；
- `make_template` → 富模板结构（板块 / 提示 / 表头）与落库；
- `PLAN_TEMPLATE_GUARD` 含「不得增删板块」与「依据不足」两条约束。

另有 jsdom 真 DOM 回归（临时脚本，不入库）：卡片渲染、② 请求体、选择记忆、普通答疑零卡片、零运行时错误。
