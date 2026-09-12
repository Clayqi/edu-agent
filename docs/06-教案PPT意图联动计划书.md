# 计划书 · 教案/PPT 意图联动与对话内导出（v1.10 提案）

> 需求原话：*提示词优化。当 agent 的生成层运作的时候，并且检索层检索到关于「教案」「ppt」，
> 给用户两个选项：1) 让 agent 生成模板；2) 在教案中心按照模板（如果有多模板给出选项）。
> agent 在对话的时候，给出如教案中心的导出功能，你可适当帮我优化，并且给我一份计划书。*
>
> 状态：**待评审**（本文只做设计，不含代码改动；批准后按 §7 分阶段实施）

---

## 1. 目标与验收标准

| # | 目标 | 验收标准（可验证） |
|---|---|---|
| G1 | 生成层运行且判定为**教案/PPT 需求**时，在对话里给出**两个选项** | 对话消息下出现选项卡：① 生成模板 ② 按模板生成（多模板时可选）；不满足条件时**不出现**（不打扰） |
| G2 | 选项①：**让 Agent 生成模板** | 产出一份新教案模板（板块结构 + 每板块填写提示），落 `content/templates/`，可在教案中心直接编辑 |
| G3 | 选项②：**按模板生成** | 选模板 → Agent 按该模板的板块骨架生成 → 内容按板块填充 → 可在教案中心继续编辑；多模板时给出选择 |
| G4 | 对话里也能**导出**（对齐教案中心） | 教案消息下出现：导出 Word / 生成 PPT / 导出 HTML / 预览 PPT + 导出位置 + 下载到本机 |
| G5 | **提示词优化** | 三个提示词改造：A 的答疑不越界写教案并引导选项；B 严格按模板骨架输出；新增「生成模板」专用提示词 |
| G6 | 不回归 | 全量 `unittest` 全绿；无教案/PPT 意图的普通答疑**行为不变**（不出现选项卡） |

**不做**（明确划界）：不做 PPT 自动排版美化、不做图片生成、不改 WPS 适配层（`feat/wps-adapter` 保持独立）。

---

## 2. 现状与可插入点（已核对代码）

| 环节 | 位置 | 现状 | 可用的信号 |
|---|---|---|---|
| 意图路由 | `routing.py: decide()` | `PLAN_HINTS` 含「教案/备课/教学设计/课件/教案模板…」，**不含「ppt/幻灯片/演示文稿」** | 单个事实来源，扩词只改这里 |
| 聊天派单 | `web_server._chat_gen` → `_code(preset)`；`auto` 走 `routing.decide` | 已有 A/S/B 三条流 | 派单结果可决定是否给选项 |
| Agent A 生成 | `generate.ask_stream()` | **内部**先 `retrieve()` 拿 hits，再流式生成；事件 `status/delta/done` | **hits 就在这里**，是判定「检索到教案/PPT」的最佳位置 |
| Agent B 教案 | `planner.make_plan(kp, goal, template=…)` | **已支持模板**：`build_messages()` 内联注入「必须使用的模板」约束 + `template_sketch(template)`；缺省 `get_current()`。聊天侧 `_stream_planner` 传的是 `req.template_id`（`ChatReq` 默认 `"default"`） | 选项②**只缺「让用户选模板」**：会话里目前永远用 default/当前模板 |
| 模板库 | `template_spec`（v1 骨架）/ `template_rich`（v2 富）/ `/api/templates` | 列表含 `rich` 标记；`_current.json` 记当前模板 | 多模板选择的数据源 |
| 导出能力 | `/api/wps/export`（`kind=docx|pptx`、`template`、`outDir`、`open`）、`/api/wps/download`；前端 `dzExportHTML()`、`dzPreviewPPT()` | 已具备全部导出形态 | 选项卡与导出条直接复用 |
| 对话 UI | `static/index.html: addActions(el, raw, q)`、`handleEv()` 的 `done` 分支 | 目前只有「复制/重新生成」 | 新增按钮/卡的落点 |
| 板块填充引擎 | `src/edu_agent/plan_sync.py`（**已撤回**，标签 `reverted/plan-sync-20260912`） | 解析 Markdown→匹配模板板块→按结构填充，15 例测试 | 选项②的填充可直接复用它（`git cherry-pick`） |

**关键判断**：教材语料里不会真的出现「教案/PPT」正文，所以「检索到关于教案/ppt」应落成**两类信号**：

1. **意图信号**：问题/指代里含 `教案|备课|教学设计|课件|ppt|幻灯片|演示文稿|模板|讲稿`；
2. **检索信号**：命中的片段/来源里含上述词（典型场景：老师**上传过教案/课件 PDF**，走 `corpus=pdf:<name>` 检索）。

命中任一 → 认为「本次涉及教案/PPT」，进入选项流程。

---

## 3. 交互设计（对话里长什么样）

```
┌─ Agent B · 教案 Agent ─────────────────────────────┐
│ 【教案正文（按模板骨架分板块，带 [n] 引用）】        │
│                                                    │
│ [复制] [重新生成]                                   │
│ ┌─ 下一步 ───────────────────────────────────────┐ │
│ │ 要把它变成可复用的东西吗？                       │ │
│ │ ① 生成教案模板（抽成板块骨架，可反复套用）        │ │
│ │ ② 按模板生成  [当前模板 ▾]  → 开始                │ │
│ └────────────────────────────────────────────────┘ │
│ 导出： [Word] [PPT] [HTML] [预览PPT]  位置:[…] [选择…] [下载到本机] │
└────────────────────────────────────────────────────┘
```

规则：

- **选项卡只在需要时出现**：`涉及教案/PPT` 且（是 B 的教案回答 或 A 的回答被判定为“可转教案”）。
  普通答疑（“什么是单调性”）**不出现**。
- **模板下拉**：`/api/templates` 返回多个时给下拉（默认选中当前模板）；**只有一个时不显示下拉**，直接按钮。
- **导出条**：出现在教案类回答下方（选项①产出的模板、选项②/直接生成的教案都算）。
- 选项是**可重复使用**的：同一份内容可以先生成模板、再按另一个模板生成。
- 全部按钮都在消息内就地处理，**不跳页**；产物仍进入教案中心模板编辑器（延续现有习惯）。

---

## 4. 技术方案

### 4.1 提示词优化（`prompts.py`）

> **先纠正一个事实**：模板骨架约束**已经存在**，但不在 `prompts.py`，而是内联在
> `planner.build_messages()` 里（原文：*「本次教案必须使用的模板（板块名称与顺序严格照此产出，
> 不得增删板块；表格板块请输出为 Markdown 表格；板块标题若含具体课题名…其余标题措辞保持模板原样）。
> 篇幅纪律：内容精炼可上课用…」*）。
> 所以提示词这块的工作是**收敛 + 补强**，不是从零加。

| 提示词 | 改动 | 为什么 |
|---|---|---|
| `SYSTEM_PROMPT`（A 答疑） | **新增第 8 条**：不越界写教案——若问题本质是「要教案/课件」，除简要作答外，用一句话说明「可点下方按钮生成模板或按模板生成」，**不要自己排版教案** | 避免 A 与 B 抢活、答非所问；也避免撑爆答案篇幅上限（现约束 300~500 字） |
| `PLAN_SYSTEM` + 骨架约束 | ① 把 `planner.py` 里那段内联骨架约束**收敛进 `prompts.py`**（成为 `PLAN_TEMPLATE_GUARD`，`planner` 只负责拼装）；② **补一条缺失规则**：骨架里有、但检索片段确实没有依据的板块，写「**本板块教材依据不足，请补充**」而**不是删掉或编内容** | 现有约束只说“不得增删板块”，没说“没依据时怎么办”——这正是生成空话/幻觉的口子 |
| **新增** `TEMPLATE_SYSTEM` + `TEMPLATE_JSON` | 依据教材片段与课题产出**教案模板**：`{title, blocks:[{title, level, hint, expect:"文本|表格", table_head?:[…]}]}`；`hint` 写该板块该填什么 | 选项①的核心；产出可直接转成 `template_rich` 富模板（含表格板块表头） |
| **新增** `CHOICE_HINT` | 一句话注入：本次涉及教案/PPT 时，可在答案末尾提示「可用下方按钮生成模板 / 按模板生成」——**具体选项由系统渲染，不要写进 JSON** | 让模型话术与 UI 一致，但**不依赖模型输出结构化选项**（可靠性优先） |

> 说明：**选项卡由服务端事件驱动**，不靠模型自觉输出；提示词只负责「话说得对」和「内容按骨架来」。
> 这样即使模型跑偏，功能也不会失效。

### 4.2 后端

**a) `routing.py`（唯一事实来源，先扩词）**

```python
PLAN_HINTS += ("ppt", "PPT", "幻灯片", "演示文稿", "课件制作", "说课", "讲稿")
TOPIC_HINTS = ("教案", "ppt", "幻灯片", "演示文稿", "课件", "教学设计", "备课")

def involves_plan_topic(text: str, hits=None) -> bool:
    """意图词 或 命中片段的来源/标题含教案/PPT 词 -> True"""
    if any(h.lower() in (text or "").lower() for h in TOPIC_HINTS): return True
    for h in (hits or []):
        blob = f"{h.metadata.get('source','')} {h.metadata.get('heading','')} {h.text[:80]}"
        if any(k in blob.lower() for k in TOPIC_HINTS): return True
    return False
```

**b) 生成层给信号（不改变现有事件语义，只**追加**）**

- `generate.ask_stream()`：命中 `involves_plan_topic()` 时，在 `done` 事件里追加
  `"plan_options": {"suggest": true, "reason": "intent|retrieval"}`；
- `web_server._chat_gen()`：在 `done` 之后追加一个新事件（老前端会忽略，天然向后兼容）：

```json
{"t":"options","kind":"plan",
 "options":[{"id":"gen_template","label":"生成教案模板","hint":"抽成板块骨架，可反复套用"},
            {"id":"use_template","label":"按模板生成","templates":[{"id":"default","name":"完整课时模板（默认）","blocks":7,"rich":false}, …],
             "current":"default"}]}
```

**c) 两个新接口**

| 方法 | 路径 | 入参 | 行为 | 返回 |
|---|---|---|---|---|
| POST | `/api/plan/template` | `{session_id?, markdown?, topic?, save?:true}` | 取会话里最近教案（或传入 Markdown/课题）→ `TEMPLATE_SYSTEM` 生成模板 → 转 `template_rich` 存库 | `{ok, template_id, name, stats, template}` |
| POST | `/api/plan/from-template` | `{session_id?, markdown?, template_id}` | Agent B 按该模板骨架生成（`planner.make_plan(template=…)`）；若已生成正文则直接**按板块填充**（复用 `plan_sync`） | `{ok, template, report, stats}` |

> 选项②两条实现路径：**重新生成**（没现成教案内容时）与**填充已有正文**（有内容时，用 `plan_sync`）。
> 前者复用现成能力，后者 cherry-pick 撤回的实现。

### 4.3 前端（`static/index.html`）

1. `handleEv()` 新增 `else if(t==='options'){ renderPlanOptions(bodyEl, ev); }`；
2. `renderPlanOptions()`：渲染选项卡（按钮 + 模板下拉 + 记忆上次选择 `localStorage: edu_tpl_pick`）；
3. 抽公共函数给对话用（**不复制粘贴**教案中心的实现）：
   - `exportHtmlFromMarkdown(md, title)`、`previewPptFromMarkdown(md)` ← 由现有 `dzExportHTML/dzPreviewPPT` 抽出，教案中心与对话共用；
   - `exportViaServer({payload|template|markdown, kind, outDir})` ← 统一走 `/api/wps/export`，结果条 + 「下载到本机」；
4. `addActions()` 增加第三个按钮组：教案类消息才挂「导出条」（Word/PPT/HTML/预览 + 位置 + 选择 + 下载）。

### 4.4 数据流

```
用户提问
  → routing.decide（意图） ─┐
  → generate/planner 内 retrieve() → hits ─┤ involves_plan_topic()
                                            ↓
                        ┌───────────── true ─────────────┐
                        │ done 事件加 plan_options        │
                        │ + options 事件（模板清单）       │
                        └───────────────┬────────────────┘
                                        ↓ 前端渲染选项卡 + 导出条
        ① 生成模板 ─→ /api/plan/template ─→ 存模板 ─→ 教案中心（可编辑）
        ② 按模板生成 ─→ /api/plan/from-template ─→ 填充 ─→ 教案中心（可编辑）
        导出 ─→ /api/wps/export + /api/wps/download（复用）
```

---

## 5. 适当优化（超出原话、建议采纳）

1. **不打扰原则**：选项卡只在意图/检索命中时出现；否则保持现状（普通答疑零变化）。
2. **一问两用**：A 的答疑结果若涉及某节知识，也允许「把它转成教案」（很多人先问概念再要教案）。
3. **模板记忆**：下拉记住上次选择，减少重复操作。
4. **生成前预检**：选模板后先显示「该模板 12 个板块，其中 3 个是表格」+ 预计耗时（教案生成 1~4 分钟），避免误点长等。
5. **空板块提醒**：生成/填充后统计「依据不足的板块」，在教案中心顶部黄条提示（复用现有 `_sync` 提示位）。
6. **导出前置校验**：导出前检查 WPS 能力开关（`/api/capabilities`）与导出目录可写，失败给明确文案而不是静默。
7. **向后兼容**：新增 SSE 事件与接口都是**追加**；旧前端忽略未知事件，旧接口签名不变。
8. **可测性**：所有判定（意图/检索/选项）都做成纯函数，便于离线单测。

---

## 6. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 选项卡误触发（把普通答疑当教案） | 打扰用户 | 双信号 + 阈值；加开关（设置里「教案选项自动提示」可关） |
| 模板骨架与教材内容不匹配（骨架有板块但检索无依据） | 生成空话 | `PLAN_SYSTEM` 要求写「依据不足，请补充」而不是编；报告里列出空板块 |
| 多模板选择造成困惑 | 操作变长 | 单模板不给下拉；记住上次选择；默认高亮当前模板 |
| 生成耗时（教案 1~4 分钟） | 用户以为卡死 | 预检提示 + 流式状态 + 可中断（沿用现有 `BUSY` 机制） |
| 与 `feat/wps-adapter` PR 混在一起 | 评审范围变大 | 独立分支 `feat/plan-link`，基于 `main`，WPS 适配层不动 |
| 撤回过的 `plan_sync` 复用引入旧问题 | 回归 | cherry-pick 后先跑它自带的 15 例 + 新加的回归用例 |

---

## 7. 实施步骤（分 3 期，每期可独立验收）

### 一期 ✅ 已完成（2026-09-12）

| 项 | 落地位置 | 实测 |
|---|---|---|
| 意图扩词（ppt/幻灯片/演示文稿/说课 + 口语「备一节…课」） | `routing.PLAN_HINTS` | 「帮我备一节 3.3 幂函数的课」路由 → **B**（此前判 A） |
| 教案/PPT 判定（意图 + 检索双信号） | `routing.involves_plan_topic()` | 意图命中→`intent`；命中片段含「教案/课件」→`retrieval`；普通答疑→`False` |
| A 不越界写教案并引导选项 | `prompts.SYSTEM_PROMPT` 第 8 条 | —— |
| 骨架约束收口 + 补「依据不足」规则 | `prompts.PLAN_TEMPLATE_GUARD`（planner 改为引用） | 单测校验含「不得增删板块」与「本板块教材依据不足」 |
| 生成层带信号 | `generate.ask_stream()` done 事件加 `plan_options` | 普通答疑 `plan_options=None` |
| `options` 事件（含模板清单） | `web_server._plan_options_event()` + `_with_plan_options()` | A 有信号→`reason=intent/retrieval`；B 恒给→`plan_mode` |
| 选项① 真正生成模板 | `planner.make_template()` + `template_obj_to_rich()` + `POST /api/plan/template` | **14s** 产出《新授课通用教案模板》：**9 板块 / 3 个表格板块**，含填写提示与表头，落库为 `rich=true` 可编辑 |
| 选项② 真的用上所选模板 | 前端 `CHAT_TPL` + `sendText(val,{preset,templateId})`（**此前 `template_id` 写死 `default`**） | 点②后请求体 = `{preset:'B', template_id:'新授课通用教案模板'}`，选择记忆在 `localStorage: edu_chat_tpl` |
| 选项卡 UI | `renderPlanOptions()`（`.plan-choice` 卡片 + 模板下拉） | 有事件→渲染两个按钮+下拉（显示板块数与「可编辑」）；无事件→**不出现** |
| 顺手修 | `prompts.JSON_INSTRUCTION` 的 `\subseteq`/`\frac`/`\log` 无效转义（历史遗留 SyntaxWarning） | 改为 raw string，行为不变 |
| 测试 | `tests/test_plan_link.py` **18 例** | 全量 **161 例全绿** |

**一期验收对照**：✅ 涉及教案的问题出现选项卡；✅ 普通答疑不出现（零打扰）；✅ 两个选项都能用（① 生成模板落库、② 按所选模板生成）。

### 二期（待办，约 1 天）
5. cherry-pick `plan_sync` + `/api/plan/from-template`（把已有教案正文**按板块填充**，而不只是重新生成）；
6. 教案中心联动：生成后自动载入模板编辑器；空板块黄条提示。

### 三期（待办，约 0.5 天）
7. 对话里的导出条（Word/PPT/HTML/预览 + 位置 + 下载），抽出与教案中心共用的函数；
8. 模板记忆打磨、生成前预检、导出前置校验、设置开关、文档 + 全量回归。


---

## 8. 测试计划

- **离线单测**：意图判定（含 ppt/幻灯片/上传教案 PDF 的检索信号）、选项生成条件、模板生成 JSON 解析、按模板生成的骨架一致性、填充（沿用 `plan_sync` 15 例）。
- **接口测试**：两个新接口的入参组合（有/无 markdown、有/无 session、单/多模板、模板不存在）。
- **前端回归（jsdom 真 DOM）**：选项卡出现/不出现、模板下拉、点① ② 的结果落点、导出条四种形态、零运行时错误。
- **人工验收**：真实会话里问「帮我备一节 3.3 幂函数的课，要课件」→ 出现选项 → 走两条路径各一次 → 导出 Word/PPT 各一次。

---

## 9. 交付物与工作量

| 交付物 | 位置 |
|---|---|
| 代码 | `routing.py`、`prompts.py`、`generate.py`、`web_server.py`、`static/index.html`、`plan_sync.py`（复用）、`planner.py`（小改） |
| 测试 | `tests/test_plan_link.py`（新）、`tests/test_plan_sync.py`（复用） |
| 文档 | `docs/07-教案PPT意图联动.md`、`CHANGELOG` v1.10.0 |
| 分支 | `feat/plan-link`（基于 `main`，与 WPS 适配层解耦） |

**合计约 2 人日**（一期 0.5 / 二期 1 / 三期 0.5）。可先只做一期看效果再决定是否继续。

---

## 10. 需要你拍板的 3 件事

1. **触发口径**：只在「路由判为教案/PPT 意图」时给选项，还是**再加**「检索命中上传的教案/课件 PDF」也算？（我建议两者都算，见 §4.2）
2. **选项①产物的粒度**：生成「纯板块骨架」（轻，老师自己填），还是「骨架 + 每板块填写提示 + 表格表头」（重，但可直接生成教案）？（我建议后者）
3. **实现顺序**：先做一期（提示词+选项卡）给你看效果，还是一次性做完三期？
