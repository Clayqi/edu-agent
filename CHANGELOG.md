# 变更记录（CHANGELOG）

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)；版本号跟界面显示对齐。

## [v1.12.0] - 2026-09-12

### 新增
- **可以删除已保存的模板**（教案中心 → 教案模板那一行的「**删除**」，详见 `docs/10-教案模板导入与编辑.md`）：
  - **软删，不硬删**：`<id>.json` 与原件 `orig/<id>.docx` 一起移到
    `content/templates/_trash/<时间戳>_<id>/`，需要时手工找回。模板是老师自己导入/整理出来的资产，
    误点一下不该就没了（这个项目刚踩过「保存时把原件删了」的坑，不再冒同类风险）。
  - **删的若是当前模板 → 当前自动切回内置 `default`**，否则 Agent B 会指向一个不存在的模板。
  - **内置 `default` 删不掉**（保底的那份）；但若曾「保存为模板」覆盖过它，删掉存档即**恢复内置骨架**。
  - 确认框写清后果（移到哪、原件一并移走、当前会切回 default）；正在编辑的模板被删则自动退出模板模式。
  - 新接口 `POST /api/template/delete`；`content/templates/_trash/` 加进 `.gitignore`（老师的数据，不入库），
    它也不会出现在模板下拉里。
- 附件：`tests/test_template_rich.py` 新增 6 例（软删搬家、删当前→切回 default、不存在/缺 id 报错、
  内置不可删、删 `default` 覆盖版恢复内置、接口包装）；全量 **208 例通过**。
- jsdom 真 DOM 回归新增第 7 个场景：未选模板不发请求、确认框点「取消」不发请求、确认后请求体正确、
  提示语与回收站路径都显示；零运行时错误。

## [v1.11.0] - 2026-09-12

### 新增
- **对话里的导出条（三期）**：教案类回答（Agent B / 总指挥出的教案）下方多一条导出条，
  与教案中心**同一套实现**——新增共用层 `expViaServer` / `expResultHtml` / `expGate` / `expDownloadHtml` /
  `expPreviewSlides`，`dzExportRun`（编排台）与 `tplExport`（模板工作台）已改为调用它，**不是复制粘贴**
  （详见 `docs/12-教案PPT意图联动.md` §6）：
  - **Word**：经 WPS 导 `.docx`（未落盘自动 python-docx 兜底）；**PPT**：本地生成真 `.pptx`，每环节一页；
  - **预览 PPT**：先看会生成哪几页，**不写文件、不用 WPS**（新接口 `POST /api/plan/preview`）；
  - **HTML**：教案 Agent 回答时服务端已落了一份网页版（`content/plans/<课题>.html`），直接给下载/新标签打开
    （此前那份 HTML 生成了却从没露过面）；
  - **位置**：选导出目录，与教案中心**共用**同一个记忆（`edu_dz_outdir`）。
  - 历史恢复的教案回答也会挂导出条；服务端 HTML 按会话只存一份（`last_html`），只挂到最近一条教案上，避免张冠李戴。
- **生成前预检**：选模板/换模板时卡片提示立刻给出「N 个板块（含 M 个表格）· 可编辑/骨架 · 生成约 1~4 分钟」；
  `/api/templates` 每项新增 `tables` 字段。
- **设置开关**：设置 → 教案 → 「教案选项自动提示」可关掉选项卡（`localStorage: edu_plan_auto`，默认开），
  同处显示当前导出位置。

### 修复
- **对话里导出 PPT 几乎空白**：`pptx_native` 的 markdown 分支**只认 `## ` 标题**，而 Agent B 的教案用的是
  `**板块名**` + `### 环节（约 X 分钟）`——两者都对不上，于是只出封面。改为抽出
  `wps_export.slides_from_markdown()`（`###` 环节 > `**板块**` > `## ` 标题 > 整篇一页，三级回退），
  并在幻灯片上去掉 `[1]` 引用角标（投影给学生看，角标是噪音）、表格内容不进 PPT（留给 Word）。
  **预览与实际生成共用这一个解析**，所以预览看到的就是会生成的。
- **导出失败可能被静默**：能力开关被关时，服务端返回 `{ok:false, gate:"capability"}`，前端现在把它翻译成
  「WPS Office 服务已关闭，请到「MCP 服务」开启」写进结果行——而不是只弹一个模糊的 toast。
  客户端已知关闭时更是在**发请求前**就拦下（实测 0 个请求）。

### 兼容性
- `POST /api/plan/preview` 刻意**不查能力开关**（不落盘、不碰 WPS）；导出接口仍受开关约束。
- `/api/templates` 每项新增 `tables` 字段（旧字段不变）。
- 附件：`tests/test_wps_tools.py` 25 例（新增 7 例锁住 Markdown→PPT 页的形状）、`tests/test_plan_link.py` 22 例；
  全量 **202 例通过**（skipped=2 为需真 WPS 的用例）。
- jsdom 真 DOM 回归扩到六个场景，新增：导出条五种按钮 + 预览 4 页 + 能力关闭时前置校验直接拦下不发请求 +
  设置关掉后不再弹卡片（打开即恢复）；全程零运行时错误。

## [v1.10.1] - 2026-09-12

### 修复
- **点③报「模板 default 不是可编辑模板（也没有原件可升级）」**——一条死胡同，两个原因都修了：
  - **卡片下拉永远预选 `default`**：`CHAT_TPL` 的初值写死 `'default'`（真值），
    于是 `CHAT_TPL || use.current` 永远取不到服务端给的「当前模板」。改为初值 `''`（= 还没选过），
    由 `use.current` 兜底；并加一道保险——记忆里的模板若已不在列表里，回到 `use.current` 而不是静默落到第一项。
  - **骨架模板本来就不该填不了**：原先只认 v2 富模板或 `orig/` 有原件的模板，其余一律报错。
    可老师要的只是「把教案按这套板块排好」，而起填充只需要**板块标题**——新建
    `plan_sync.rich_from_skeleton()`：把 v1 骨架（含内置 `default`）现搭成可填充的富模板，
    表格板块还能从 note 里把表头（`表头: 环节 / 教师活动 / …`）还原回去。
    响应新增 `template_source`（`rich` / `upgraded` / `skeleton`）说明走的是哪条。
  - 实测内置 `default`：7 板块，教学目标/重难点/教学过程/板书设计/作业布置 **5 个 1.0 命中**。
- **`get_template("default")` 无条件返回内置骨架**：把默认模板填好再「保存为模板」后，
  教案中心显示的是填好的那份、Agent B 却还在用内置骨架。改为**同名存档文件优先**（文件不存在才用内置）。

### 兼容性
- `POST /api/plan/from-template` 不再对骨架模板报错；响应新增 `template_source` 字段（旧字段不变）。
- 全量 **192 例通过**（skipped=2 为需真 WPS 的用例）。

## [v1.10.0] - 2026-09-12

### 新增
- **教案/PPT 意图联动（二期）：选项③「填入教案中心」**——**不再花模型调用**，把会话里已有的一份教案
  按标题填进模板对应板块，直接进教案中心继续编辑（详见 `docs/12-教案PPT意图联动.md` §5）：
  - `src/edu_agent/plan_sync.py`（从撤回的提交取回）：`parse_plan_markdown`（认 `# 课题` / `**板块名**` /
    `### 环节` / 列表 / Markdown 表格，剥掉会话标签前缀）→ `match_sections`（标题归一化 + 别名组
    「作业设计↔作业布置、教材依据↔课标依据…」+ 字符 Jaccard，**贪心 1:1 分配**，阈值 0.34）→
    `fill_template`（表格板块保留**真表头**并一环节一行、其余逐条成段并套用模板字体字号；
    **模板板块顺序/标题/格式一律不动**，没匹配到的保持原样，多出来的追加为新板块，不丢内容）。
  - 新接口 `POST /api/plan/from-template`：返回填充后的富模板 + 报告
    （`matched` / `appended` / `unmatched_blocks` / `blank_blocks`）；`markdown` 留空时会话里最近一份教案兜底；
    骨架模板有原件时现场升级再填。默认**不落盘**，交给编辑器改完再「保存为模板」。
  - 卡片第三项**仅在会话里真有教案正文时出现**（`_last_plan_markdown` 判定，避免给一个没东西可填的按钮）。
  - **② 按模板生成完成后自动填入**教案中心（`done` 事件触发），卡片给填充报告；
    **不抢视图**——内容进编辑器并落草稿，老师自己切页（自动跳页会打断正在看回答的人）。
  - 教案中心编辑器顶部新增两条：灰条（填充报告）+ **黄条**（N 个板块没匹配到、J 个还空着）。
    同一个板块既没匹配到又空着时不重复计数。
- `plan_sync.blank_blocks()`：判定「还空着」的板块（没有元素，或只剩模板占位文字/只有表头的空表格）。

### 修复
- **升级模板后保存会删掉模板原件**（数据丢失）：`/api/template/upgrade` 把模板**自己的原件**
  `content/templates/orig/<id>.docx` 当成「上传临时件」写进 `_upload_path`，保存时被 unlink——原件就没了。
  改为 `_keep_source` 标记 + 只有位于配置数据目录（`EDU_DATA_DIR`）内的临时件才允许删 +
  `save_rich` 遇「源==目的」不再自拷。该修复原随「会话教案同步」一起被撤回，本次独立补回
  （功能可撤，修复不该跟着撤），并补回归 `TestUpgradeDoesNotDeleteOriginal`。
- **填充进模板表格的「表头」问题**：模板该板块的表格首行不是真表头时（如「数学抽象 | 通过分析…」这种
  标签+长正文的行），填充结果仍被标 `header: true`——内容行被当表头加粗，而且空板块判定会跳过首行，
  出现「明明填了却报空」。改为按实际识别结果标 `header`。
- **① 生成的模板里段落板块的填写提示没有前缀**（只有表格板块带 `（填写提示）`）：
  统一加前缀，一眼能分出「这是提示」还是「这是内容」，空板块判定也据此。

### 兼容性
- `options` 事件的 `options` 数组新增第三项 `fill_center`（仅当会话里有教案正文时下发）；
  老前端只渲染它认识的 `gen_template` / `use_template`，不受影响。
- 附件：`tests/test_plan_sync.py`（21 例）、`tests/test_plan_link.py`（19 例）、`tests/test_template_rich.py`（16 例）；
  全量 **186 例通过**（skipped=2 为需真 WPS 的用例）。
- jsdom 真 DOM 回归三场景：③ 请求体与报告、② 生成后自动填入（走真实接口，编辑器载入 12 板块 / 18 段 / 6 表）、
  普通答疑零卡片；零运行时错误。

## [v1.9.0] - 2026-09-12

### 新增
- **教案 / PPT 意图联动（一期）**：对话里问到教案、课件、PPT 时，回答下方多一张「下一步」选项卡，
  给老师两条路（详见 `docs/12-教案PPT意图联动.md`，规划见 `docs/11-教案PPT意图联动计划书.md`）：
  - **① 生成教案模板**：教案 Agent 把课题归纳成**板块骨架 + 每板块填写提示 + 表格板块表头**，
    转成可编辑富模板存入 `content/templates/<id>.json`（`spec_version: 2`，与「导入 .docx / 全量编辑」同一模型），
    卡片上直接给「去教案中心编辑」入口。实测 14 秒产出《新授课通用教案模板》9 板块 / 3 表。
  - **② 按模板生成**：模板多于 1 个时给**下拉选择**（显示板块数与是否可编辑），选中后按该模板的板块名称与顺序
    重新生成教案；**选择被记住**（`localStorage: edu_chat_tpl`）。
  - 新接口 `POST /api/plan/template`（`topic` 留空时取会话里最近一份教案的课题）。
- **触发判定** `routing.involves_plan_topic()`：两类信号任一命中即给选项——问题里有教案/PPT 词（`intent`），
  或**检索命中片段**的来源/标题/正文含这些词（`retrieval`）；派单结果为 B 时恒给（`plan_mode`）。
  **普通答疑零打扰**（有专门回归用例）。
- 提示词：`prompts.PLAN_TEMPLATE_GUARD`（骨架约束从 planner 收口到 prompts，并补「本板块教材依据不足，请补充」规则）。

### 修复
- **教案类口语/PPT 说法被误判成答疑（A）**：`routing.PLAN_HINTS` 原先只有「课件」没有「ppt」，
  且不含口语「备一节…课」，导致「要 ppt」「帮我备一节 3.3 幂函数的课」都走 A。
  已补 `ppt`、`幻灯片`、`演示文稿`、`slides`、`课件制作`、`说课`、`备一节`、`备一课`、`备这节课`。
- **对话里的「按模板生成」实际没生效**：前端发 `/api/chat` 时 `template_id` **恒为 `'default'`**，
  「选模板」传不到后端。改为 `CHAT_TPL` + `sendText(val,{preset,templateId})`；后端链路一行未改
  （`/api/chat` → `_stream_planner` → `planner.make_plan(template=...)`）。
- **Agent A 越界写教案**：`SYSTEM_PROMPT` 增第 8 条——A 不产出教案，改为引导用户点那两个选项。
- `prompts.JSON_INSTRUCTION` 里 `\subseteq` / `\frac` / `\log` 的无效转义（历史遗留 `SyntaxWarning`）改为 raw string，行为不变。

### 兼容性
- SSE 事件类型新增 `options`（`kind: "plan"`），**老客户端会忽略不认识的 `t`**，属加法变更；
  `done` 事件新增可选字段 `plan_options`（不涉及教案时为 `null`）。
- 附件：`tests/test_plan_link.py`（18 例，全离线）——派单补词、三类触发路径、事件形状、模板生成结构、约束文案。
  全量测试 **161 例通过**。

## [v1.8.0] - 2026-09-11

### 新增
- **教案中心：导入自有教案模板 + 全量编辑**（`src/edu_agent/template_rich.py` + 教案中心模板工作台，
  详见 `docs/10-教案模板导入与编辑.md`）：
  - **导入 .docx**：按正文顺序解析成「板块 / 段落 / 表格」结构，**逐 run 保住字符格式**
    （加粗/斜体/下划线/中文字体/字号/颜色）与段落格式（对齐/行距），板块标题连自身格式一起存；
    标题判定比旧骨架更严格，不再把「教学重点：理解函数的概念，掌握…」这类整句正文当成板块名。
  - **全量编辑**：板块改标题/层级/上下移/增删；段落改文字/增删/上下移；表格改单元格/增删行列/删表；
    格式工具栏（B/I/U、字体、字号、颜色）+ 段落对齐。所见即所得，草稿自动存浏览器。
  - **两处去向**：① 按模板**导出 Word / PPT**（走既有导出链，含自选目录与「下载到本机」）；
    ② **保存为模板**并设为 Agent B 当前模板——落 `content/templates/<id>.json`（`spec_version: 2`），
    `template_spec.get_template()` 读到 v2 自动派生骨架，模板列表只有一个。
  - 老式「骨架模板」（v1）可用 `content/templates/orig/` 里的原件**一键升级**成可编辑版。
  - 新接口：`POST /api/template/import`、`POST /api/template/upgrade`、`GET /api/template/rich`、
    `POST /api/template/rich/save`、`GET /api/template/blank`；`POST /api/wps/export` 增加 `template` 直出。
  - 附件：`tests/test_template_rich.py`（13 例，全离线）。**边界**：图片不保留（导入为占位、导出跳过并报数）、
    不解析页眉页脚/分页符/复杂版式。

### 修复
- `/api/templates` 的 `current` 恒为 `default`：原实现用 `get_template("")`，而它遇到空 id 会直接返回默认模板；
  改为 `get_current()`（读 `content/templates/_current.json`）。模板下拉的选中态与「当前模板」由此才准。

## [v1.7.0] - 2026-09-10

### 新增
- **WPS Office 能力集成**（源自 [lc2panda/wps-skills](https://github.com/lc2panda/wps-skills)，MIT）：
  **第三方源码不入库**（交接要求见 `docs/09-WPS接入交接要求.md`）——由 `deploy/setup_wps_mcp.cmd`
  克隆到仓库外（默认 `%LOCALAPPDATA%\edu-agent\deps\wps-skills`）并 `npm ci && npm run build`，
  再用 `deploy/patch_wps_mcp.ps1` 打 11 处本地补丁，最后写 `data/wps_mcp.json`（含上游 commit 版本锁）。
  实测 **250 个工具**；Windows 走 `scripts/wps-com.ps1` 的 PowerShell COM 桥，**无需安装 WPS 加载项**。
  - 路径解析优先级：`WPS_MCP_ENTRY` > `WPS_MCP_DIR` > `data/wps_mcp.json` > 默认位置；
    `.gitignore` 加护栏 `mcp_servers/wps-office-mcp/`、`skills/` 防第三方回流。
  - **统一能力开关** `src/edu_agent/capabilities.py`：MCP 服务与 Skill 共用一套开关，**默认全开**，运行态落 `data/capabilities.json`；关闭后客户端直接短路，不起子进程、不碰 WPS。
  - 新接口：`GET /api/capabilities[?deep=1]`、`POST /api/capabilities/toggle`、`GET /api/mcp/status`。
  - 「MCP 服务」页改为真实能力清单（开关 + 运行状态 + 工具数 + 依赖提示）；「Skill 市场」新增 WPS Office 分组，卡片与详情页均可开关（与 MCP 开关同源，依赖关掉时 Skill 显示「依赖已关」）。
  - 右侧「运行状态」面板新增 MCP / Skill 卡片：各服务状态、Skill 启用数、WPS 导出是否就绪。
  - 教案中心新增「**导出 Word · WPS**」与「**生成 PPT · WPS**」，并支持**自选导出位置**（目录选择器 + 手填路径，留空 = 项目内 `content/plans`）与「下载到本机」（`GET /api/wps/download`）：
    - Word：**WPS COM 优先，未落盘则 python-docx 本地兜底**（返回值 `engine` 写明用了哪条）；
    - PPT：**python-pptx 本地生成**真 `.pptx`（封面 + 每环节一页，16:9），生成后用 WPS 演示打开。
    两者**服务关掉时都被同一闸门拒绝**（返回 `gate:"capability"`）。
  - 交接文档与证据：`tools/wps_spike/README.md`（环境 / 从零步骤 / 10 条坑 / 一句话风险）+ `tools/wps_spike/evidence/`（从零安装日志、MCP 启动与握手原文、WPS 窗口截图 + OCR 复核）。
- `POST /api/wps/export` 扩展 `kind`（`docx|pptx`）与 `outDir`（自选目录，不存在自动创建）；新增 `GET /api/wps/download`（按扩展名白名单回传导出的 Office 文件）。
- 多 MCP 客户端：`mcp_tools` 支持按 id 起任意 MCP 服务，新增 `list_tools / call_tool / call_sequence`（一次 stdio 握手跑完一串调用，教案导出即用它）；保留 `ALLOWED` / `mcp_available` / `mcp_call` 旧接口。
- 适配层测试 `tests/test_wps_tools.py`（18 例）：开关闸门、路径解析（含"未安装不崩"）、导出目录与文件名净化、本地 PPT 生成；**真·WPS 用例默认 skip**（`EDU_TEST_WPS=1` 才跑）。

### 修复
- **导出后 WPS 窗口不弹出**：桥接 `Get-WpsWord` / `Get-WpsExcel` 从不设 `Visible`，经 MCP 建文档时 WPS 是「隐形启动」的。新增 `Show-WpsApp` 并接到全部 6 条取实例路径（含已运行实例）——实测导出后出现可见窗口 `3.3_幂函数.docx - WPS Office`。
- **教案中心「导出 Word · WPS」点击无反应**：`dzExportWps()` 定义在外层作用域却调用了 `dzBind()` 的局部函数
  `syncInputs()`，点击即抛 `ReferenceError`（只在控制台可见）。已把同步输入框的调用移到点击包装内，
  并给导出流程加 try/catch —— 异常会以 toast 显示，不再静默失败。
- **PPT 只能预览不能生成**：本机 WPS 演示的 COM 通道是「无头代理进程」（`wpp.exe` 窗口句柄 = 0），
  `Presentations.Add()` 出来的文稿 `Windows/Slides` 恒为 0、`Slides.Add` 返回 null、`SaveAs` 报
  `RPC_E_CALL_REJECTED`。故 PPT 改为 **python-pptx 本地生成**（4 秒出真 OOXML，无需 WPS），
  生成后用 `wps_ppt_open_presentation` 打开（这条路径是好的）。
- 桥接 `saveAs` / `save` 的 PPT 分支原先直接用 `$ppt.ActivePresentation`（无活动窗口时恒为 null），
  改为走 `Get-TargetPres`；`Get-TargetPres` 本身也增加「回落到最后一个文稿」的兜底。
- 目录选择器：`_drives()` 原写死 `"CDEF"` 且 API 默认路径是 `D:/hermes`（本机不存在），
  导致选择器一打开就报「路径不在允许范围」。改为全盘探测（C–Z）、默认回落到 `content/plans`，
  `openDirPicker` 支持 `{title, sub, start}` 参数。
- `requirements.txt` 补齐 6 个缺失依赖：`Markdown`、`python-multipart`、`rank-bm25`、`mcp>=1.2,<2`、`sympy`、`python-pptx`——缺前三个 Web/检索/上传直接报错；缺 `mcp`/`sympy` 时 edu-math MCP 工具数为 0（且 `mcp` 2.x 移除了 `mcp.server.fastmcp`，必须 `<2`）。
- 桥接 `saveAs` 的 Word 格式映射：`docx` 由 `16` 改为 `12`——WPS 把 16（`wdFormatDocumentDefault`）落成二进制 `.doc`（头 `D0CF11E0`）却顶 `.docx` 扩展名；`12`（`wdFormatXMLDocument`）才是真 OOXML（头 `504b`）。`wps_export` 增加格式哨兵，落盘非 zip 时在返回值里告警。
- 编辑 `wps-com.ps1` 必须保留 UTF-8 BOM：PowerShell 5.1 在无 BOM 时按 GBK 解析中文注释，会直接语法报错（本次踩到并已恢复）；`patch_wps_mcp.ps1` 因此强制写回带 BOM 并做语法自检。
- **Word 导出加本地兜底**：本机 WPS 11.1.0.10009 的 Writer COM 会进入「幽灵态」（`Documents.Add()` 出空壳、`insertText` 报成功不落字、`SaveAs` 报"成功"却不写盘，强杀 WPS 后易触发）——导出改为 WPS COM 优先、未落盘则 `python-docx` 本地生成，交付物一定有。
- `.cmd` 启动/安装脚本统一 GBK+CRLF（不加 `chcp 65001`）：UTF-8 会让 cmd 解析指针错位，报 `'cho' is not recognized` 之类怪错。

### 仓库
- 新增 `deploy/setup_wps_mcp.cmd`（第三方一键装到仓库外）、`deploy/patch_wps_mcp.ps1`（11 处桥接补丁，幂等）、`tools/wps_spike/`（交接文档 + 证据）、`tests/test_wps_tools.py`。
- 第三方 wps-skills 源码/dist/node_modules **一律不入库**；`.gitignore` 加护栏防回流。

## [v1.6.0] - 2026-09-10

### 新增
- **教案中心改为「教案 × PPT 可视化编排台」**（不再是聊天窗口）：左侧编排这节课的教学环节（名称 / 分钟 / 要点，支持上移下移、增删），右侧即时生成对应的 PPT 页面（每页 = 一个环节，缩略图显示标题与要点）；改左边右边立刻变，点右侧卡片跳回左侧对应环节。
  顶部：课题、学情/课时、生成骨架、添加环节、保存、导出 HTML、预览 PPT。
  数据存浏览器本地（`localStorage: edu_design_v1`），自动保存；「导出 HTML」产出含完整教案 + PPT 大纲的独立文件；「预览 PPT」按 16:9 全屏逐页展示。
- 侧栏「教育能力」分组可伸缩：点分组标题或右侧箭头收起/展开（带 0.18s 过渡），状态记 `localStorage: edu_cap_open`，刷新后保持。

### 变更
- 「教案中心」入口按角色分开：**教师** → 教案 × PPT 编排台；**学生** → AI 答疑（对话）。同一按钮双角色，不再共用对话视图。

## [v1.5.0] - 2026-09-10

### 新增
- **看原页**：`GET /api/page_image?page=N[&source=&dpi=]`，把教材原页渲染成 PNG（印刷页 `+6` = 物理页，150dpi，缓存 `data/page_cache/`）。
  前端引用卡与正文绿色引用 pill 都可点开「原页浏览器」：上一页/下一页、跳任意页、本节首/本章首、回到引用页、键盘 `←/→` 翻页、`Esc` 关闭。
- **目录页码范围**：`scripts/build_toc_ranges.py` → `content/toc_ranges.json`；`GET /api/textbook/toc` 返回每章每节页码范围（实测：第三章 p59–p102、3.3 幂函数 p89–p92、全书 p1–p260）。
- **图片/公式防幻觉机制**：`src/edu_agent/figdetect.py` 给片段判 `has_figure` / `fig_nums` / `fidelity`；`scripts/backfill_chunk_meta.py` 回填向量库 151 个片段（有图号 64、低保真 33）；`prompts.FIGURE_GUARD` + `generate._snippet_block()` 对含图片段加 ⚠ 硬约束——片段文字里没出现的公式一律当"书上只有图"，禁止写出/推导/用常识补全，只给页码+图号并提示看原页。
- 左侧栏可收起/展开（对齐 DeepSeek Harness，状态记 localStorage）。

### 变更
- 左上角面包屑显示**当前对话名称**（首问后自动命名），不再是写死的"新对话"。
- 会话消息支持附带数据（`host/store.SessionStore.append(..., meta=)`）：**引用随消息持久化**，刷新/重开会话后绿色引用 pill 与「复制/重新生成」仍在（此前刷新即丢）。

### 修复
- 右侧面板 2×2 圆钮的文字标签被下一行圆遮挡（行距不足）。
- `--ink-800` 变量在 `:root` 未定义 → 激活态圆钮标签变成白底白字看不见；已补 `#27272a`。

### 仓库
- `static/*.bak-*` 移出版本控制并写入 `.gitignore`；`content/toc_ranges.json` 随仓库走（`data/` 不入库）。

## [v1.4.0] - 2026-09-10
- 首次交付：Agent A（课本教练答疑）/ B（教案）/ S（总指挥派单）× LangChain 1.x + Chroma 151 块 + bge-m3 + DeepSeek v4-flash；UI 收口到 `web_server.py` @ 5174；`tests/` 112 例全绿。

[v1.5.0]: https://github.com/Clayqi/edu-agent/compare/v1.4.0...v1.5.0
