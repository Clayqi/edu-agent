# 变更记录（CHANGELOG）

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)；版本号跟界面显示对齐。

## [v1.7.0] - 2026-09-10

### 新增
- **WPS Office 能力集成**（源自 [lc2panda/wps-skills](https://github.com/lc2panda/wps-skills)，MIT）：
  **第三方源码不入库**（交接要求见 `edu-agent-WPS接入交接要求.md`）——由 `deploy/setup_wps_mcp.cmd`
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
