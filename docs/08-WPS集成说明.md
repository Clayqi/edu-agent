# WPS Office 能力集成说明（v1.7.0 · 2026-09-10）

把 [lc2panda/wps-skills](https://github.com/lc2panda/wps-skills)（MIT）的 WPS MCP 服务接进 edu-agent，
纳入项目统一的「能力开关」，教案中心可一键导出 Word / 生成 PPT。

> **交付边界（见 `docs/09-WPS接入交接要求.md`）**：仓库里**只有本项目的适配层 + 安装脚本**。
> 第三方源码与 `node_modules` 一律不入库，由 `deploy/setup_wps_mcp.cmd` 装到仓库外。
> 环境版本、从零复现步骤、踩坑清单与证据见 **[`tools/wps_spike/README.md`](../tools/wps_spike/README.md)**。

## 1. 仓库里有什么 / 第三方在哪

| 内容 | 位置 |
|---|---|
| 能力注册表（开关 + 状态 + 路径解析） | `src/edu_agent/capabilities.py` |
| 多 MCP 客户端 | `src/edu_agent/mcp_tools.py` |
| 教案导出（Word / PPT） | `src/edu_agent/wps_export.py` |
| 安装脚本 / 桥接补丁 | `deploy/setup_wps_mcp.cmd`、`deploy/patch_wps_mcp.ps1` |
| 适配层测试 | `tests/test_wps_tools.py` |
| 交接文档与证据 | `tools/wps_spike/`（`README.md` + `evidence/`） |
| **第三方（不在仓库里）** | `%LOCALAPPDATA%\edu-agent\deps\wps-skills`（由安装脚本克隆；`WPS_MCP_DIR` / `data/wps_mcp.json` 可改） |
| 运行态开关 | `data/capabilities.json`（不入库；删掉即回到「全默认开启」） |
| 导出产物 | 默认 `content/plans/<课题>.docx|.pptx`，可在教案中心改目录 |

安装/重装第三方（克隆到仓库外 + `npm ci` + `tsc` + 打补丁 + 写配置）：

```powershell
deploy\setup_wps_mcp.cmd              # 默认装到 %LOCALAPPDATA%\edu-agent\deps\wps-skills
deploy\setup_wps_mcp.cmd D:\deps      # 或指定位置
```

路径解析优先级：`WPS_MCP_ENTRY` > `WPS_MCP_DIR` > `data/wps_mcp.json` > 默认位置。
`.gitignore` 里加了护栏 `mcp_servers/wps-office-mcp/`、`skills/`，防止第三方被误提交。

## 2. 开关模型（默认全开）

- 注册项分 `mcp`（服务）与 `skill` 两类，**默认开启**。
- 只在用户显式关过之后才在 `data/capabilities.json` 里留痕：

```json
{ "version": 1, "mcp": { "wps-office": false }, "skill": { "wps-excel": false } }
```

- **一处关闭、处处生效**：客户端调用、教案导出、Skill 生效态共用 `capabilities.is_enabled()`。
  - 关闭 MCP 服务 → `mcp_tools._gate()` 直接返回，不起子进程、不碰 WPS；
  - 关闭 MCP 服务 → 绑定它的 Skill 显示「依赖已关」（`active=false`）；
  - 关闭 MCP 服务 → 教案中心导出返回 `{"ok": false, "gate": "capability"}`，前端提示去开启。

## 3. 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/capabilities?deep=1` | 能力清单：开关、运行状态、`detail` 原因、`tools` 工具数（`deep=1` 才做 MCP 握手，慢） |
| POST | `/api/capabilities/toggle` | `{"kind":"mcp|skill","id":"wps-office","enabled":false}` |
| GET | `/api/mcp/status` | 右栏面板用的轻量快照 + `wps_export_ready` |
| POST | `/api/wps/export` | `{"payload":{title,grade,steps:[{name,minutes,bullets}]}, "kind":"docx|pptx", "outDir":"F:\\导出目录"}`（也支持 `{"markdown":"..."}`） |
| GET | `/api/wps/download?path=<abs>` | 回传导出的 Office 文件（前端「下载到本机」），扩展名白名单 `.docx/.pptx/.doc/.ppt/.pdf` |

`outDir` 留空 = 项目内 `content/plans`；相对路径按项目根解析；不存在会自动 `mkdir`。

## 4. 教案 → .docx：WPS COM 优先 + 本地兜底

```
① WPS COM（真·集成路径，本机可用时走这条）
   wps_common_ping
   wps_execute_method {method: createDocument}       # 必须先建文档，其余动作都取 ActiveDocument
   wps_word_insert_text ×N                           # 样式：标题 1/2/3、正文、列表段落
   wps_execute_method {method: insertTable, ...}     # 环节一览表（带数据只能用这个内置工具）
   wps_common_save_as {filePath, format:"docx"}
② 若 ① 跑完但**磁盘上没有文件**（WPS 会话「幽灵态」，见 spike README 坑 #5）
   → wps_export.docx_native() 用 python-docx 本地生成同结构的 .docx
③ open_with_wps()：wps_word_open_document 打开（失败回落系统默认程序）
```

返回值里的 `engine` 会写明实际用了哪条：`wps-mcp` 或 `python-docx`；
`format_ok` 是落盘格式哨兵（真 OOXML 头应为 `PK`）。

## 4b. 教案 → .pptx（python-pptx 本地生成，不走 COM）

```
pptx_native():  Presentation() 16:9
                layout[0] 封面（课题 + 学情/环节数/总时长）
                layout[1] × N（每环节一页，正文为要点）
                prs.save(out_path) → open_with_wps()
```

实测 3 环节 = **4 页**、约 4~6s。**为什么不用 WPS COM 生成**：见 spike README 坑 #4。

## 5. 桥接补丁（`deploy/patch_wps_mcp.ps1`，11 处、幂等）

第三方源码不入库，所以补丁以**脚本 + 可核对替换**的形式留在仓库里，安装时自动施加。
补丁内容与逐条原因见 `tools/wps_spike/README.md` §4，摘要：

1. `docx` 存盘格式码 `16 → 12`（否则落成二进制 `.doc` 顶着 `.docx` 扩展名）；
2. `Show-WpsApp` 让 Writer/Excel 实例可见（原先只有 PPT 设 `Visible`，导出后窗口不弹出）；
3. `Get-TargetPres` 回落到最后一个文稿（无活动窗口时 `ActivePresentation` 为 `$null`，`saveAs` 恒失败）；
4. PPT 的 `save` / `saveAs` 改用 `Get-TargetPres`。

改完脚本会强制写回 **UTF-8 带 BOM**（PowerShell 5.1 无 BOM 时按 GBK 解析中文注释会语法报错），
并做一次 `Parser::ParseFile` 语法自检。

## 6. 实测记录（2026-09-11）

- `deep=1`：`math tools=5`、`wps-office tools=250`，两者 `enabled=true running=true`。
- 关 `wps-office` → `wps_export_ready=false`，导出返回 `gate:"capability"`；重新开启即恢复。
- 关 `wps-excel` → 只影响该 Skill（`enabled=false active=false`），不影响 `wps-word`。
- 从零安装：克隆 → `npm ci`（434 包 / 10s）→ `tsc` → 补丁 11 处全命中 → 写 `data/wps_mcp.json`（含上游 commit）。
- 导出：Word 27 步 0 失败（本机 WPS 会话幽灵态时自动走 `python-docx` 兜底，产物仍为真 OOXML 37 KB，
  内容逐项核对含标题/学情/一、教案/二、环节一览/三、PPT 大纲/要点）；PPT 4 页真 OOXML。
- 截图证据：WPS 文字窗口出现导出物，OCR 复核识别出教案正文（见 `tools/wps_spike/evidence/`）。
- 测试：`unittest discover -s tests` 共 **130 例全绿**（新增 18 例适配层用例，其中真·WPS 用例默认 skip）。
- 浏览器侧（jsdom 真 DOM 回归）：生成 PPT 4s、导出 Word 约 70s，结果条含文件名 + 路径 + 「下载到本机」，
  目录选择器标题/盘符/起始路径正确，全程零运行时错误。
- `GET /api/wps/download`：200 + `Content-Disposition: attachment`；非 Office 扩展名与不存在的文件均 404。
