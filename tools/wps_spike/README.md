# WPS MCP spike —— 从零复现步骤 + 证据（交接给 George）

> 对应 `docs/09-WPS接入交接要求.md`。本文档回答三件事：**环境是什么 / 怎么从零搭起来 / 踩过哪些坑**。
> 代码走 PR（分支 `feat/wps-adapter`），仓库里**只有适配层 + 安装脚本**，第三方源码不入库。
> 证据索引见文末 §5。

---

## 1. 我的环境（2026-09-11 实测）

| 项 | 值 |
|---|---|
| OS | Microsoft Windows 11 家庭版 中文版 · Build 26200 (10.0.26200) |
| WPS Office | **11.1.0.10009**（用户级安装：`C:\Users\<用户>\AppData\Local\Kingsoft\WPS Office\11.1.0.10009\office6\`） |
| Node | **v24.20.0**（npm 11.19.0） |
| Python | 3.13.2（项目自带 `.venv`） |
| wps-skills 版本锁 | 上游 commit **`a82533662268b3245f93d8685bc45dffede048b6`**（main，2026-06-30，`fix(install): install.ps1 补齐 publish.xml 创建…`） |
| 安装位置（仓库外） | `%LOCALAPPDATA%\edu-agent\deps\wps-skills` |
| 是否需要 WPS 加载项 | **不需要**（加载项是 macOS/Linux 的 HTTP 轮询模式；Windows 走 PowerShell COM 桥 `scripts/wps-com.ps1`） |

## 2. 从零复现（每条都是原样可跑的命令）

```powershell
# 0) 取仓库 + 装 Python 依赖
git clone https://github.com/Clayqi/edu-agent.git F:\edu-agent3
cd F:\edu-agent3
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 1) 一键装第三方 WPS MCP（克隆到仓库外 + npm ci + build + 打本地补丁 + 写运行时配置）
deploy\setup_wps_mcp.cmd
#    想换位置： deploy\setup_wps_mcp.cmd D:\deps      或先设环境变量 EDU_DEPS_DIR

# 2) 看装到哪了 / 锁的哪一版
type data\wps_mcp.json
#   {"dir":"...\\wps-skills","entry":"...\\dist\\index.js","skills_dir":"...\\skills",
#    "commit":"a82533662268b3245f93d8685bc45dffede048b6","installed_at":"..."}

# 3) 验服务能起来（会打印工具数；不碰 COM、不会弹 WPS 窗口）
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); from edu_agent import mcp_tools; print(len(mcp_tools.list_tools('wps-office')))"
#   -> 250

# 4) 只跑适配层测试（离线；真·WPS 用例默认 skip）
.venv\Scripts\python.exe -m unittest tests.test_wps_tools -v
#   想连 WPS 一起验： set EDU_TEST_WPS=1 && .venv\Scripts\python.exe -m unittest tests.test_wps_tools -v

# 5) 起服务，到「MCP 服务」页看状态（应显示：运行中 · 250 个工具）
.venv\Scripts\python.exe src\edu_agent\web_server.py      # http://127.0.0.1:5174

# 6) 真导一份教案（教案中心「导出 Word · WPS」等价命令行）
set PYTHONPATH=src
.venv\Scripts\python.exe -m edu_agent.wps_export docx "%TEMP%\wps-out"
```

**我调的哪个工具、传什么、返回什么**（原文摘录，完整见 `evidence/02-mcp-handshake.log`）：

```
>>> {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18",...}}
<<< {"result":{"protocolVersion":"2025-06-18","serverInfo":{"name":"wps-office-mcp","version":"1.0.0"},...}}
>>> {"jsonrpc":"2.0","id":2,"method":"tools/list"}
<<< 250 个工具（含 wps_word_insert_text / wps_common_save_as / wps_ppt_add_slide …）
>>> {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"wps_common_ping","arguments":{}}}
<<< {"success":true,"data":{"message":"pong",...}}      # 服务日志：ping - SUCCESS (1844ms)
```

教案导出（Word）走的是这串工具：`wps_common_ping` → `wps_execute_method{createDocument}`
→ `wps_word_insert_text ×N`（标题/正文/列表样式）→ `wps_execute_method{insertTable}`（环节一览表）
→ `wps_common_save_as{filePath,format:"docx"}`，实测 27 步。

## 3. 架构（仓库里有什么）

```
deploy/setup_wps_mcp.cmd      一键安装：clone 到仓库外 + npm ci + build + 打补丁 + 写 data/wps_mcp.json
deploy/patch_wps_mcp.ps1      给第三方桥打 11 处本地补丁（幂等、带回滚提示、改完做语法自检）
src/edu_agent/capabilities.py 能力注册表：MCP/Skill 统一开关（默认全开）+ 运行状态探测 + 第三方路径解析
src/edu_agent/mcp_tools.py    多 MCP 客户端（stdio 短连接 / 白名单 / 失败兜底；新增 list/call/call_sequence）
src/edu_agent/wps_export.py   教案 → Word/PPT 导出（Word: WPS COM 优先 + python-docx 兜底；PPT: python-pptx）
tests/test_wps_tools.py       适配层测试（门控 / 路径解析 / 白名单 / 本地生成；真·WPS 用例自动 skip）
tools/wps_spike/              本文档 + evidence/
```

路径解析优先级（**第三方永远在仓库外**）：`WPS_MCP_ENTRY` > `WPS_MCP_DIR` >
`data/wps_mcp.json` > 默认 `%LOCALAPPDATA%\edu-agent\deps\wps-skills`。
`.gitignore` 里加了护栏 `mcp_servers/wps-office-mcp/`、`skills/`，防止第三方被误提交。

## 4. 踩过的坑（这部分最值钱）

| # | 现象 | 根因 | 解决 |
|---|---|---|---|
| 1 | 导出的文件叫 `.docx`，实际是**二进制 .doc**（头 `D0CF11E0`） | 桥接把 `docx` 映射成 `16`（`wdFormatDocumentDefault`），WPS 落成 OLE2 旧格式 | 补丁改成 `12`（`wdFormatXMLDocument`）；导出侧再加 `PK` 头哨兵，落盘不是 zip 就在返回值里告警 |
| 2 | **WPS 窗口不弹出**，用户以为导出失败 | 桥接 `Get-WpsWord`/`Get-WpsExcel` 从不设 `Visible`（只有 PPT 分支设了） | 补丁加 `Show-WpsApp`，接到全部 6 条取实例路径（含"已运行实例"，能把已隐形的实例显示出来） |
| 3 | `saveAs` 报 **`No active presentation`** | 桥接 PPT 分支直接用 `$ppt.ActivePresentation`；MCP 后台建文稿时没有活动窗口 → 恒为 `$null` | 补丁改走 `Get-TargetPres`，并给该函数加"回落到最后一个文稿"的兜底 |
| 4 | 只跑通 MCP 不够：**PPT 建不出来**（`Slides.Add` 返回 null、`SaveAs` 报 `RPC_E_CALL_REJECTED`、页数恒 0） | `Kwpp.Application` 拿到的是**无头代理进程**（`wpp.exe` 窗口句柄 = 0，真界面在 `wps.exe`） | PPT 改为 **python-pptx 本地生成**真 `.pptx`，再用 `wps_ppt_open_presentation` 打开（"打开已有文件"这条路是好的） |
| 5 | 同上病理出现在 **Writer**：`Documents.Add()` 建出空壳（`path=null`、0 字符），`insertText` 报成功却不落字，`SaveAs` 报"另存为成功"却不写盘 | 强杀 WPS / 删掉它正打开的目录后，WPS 会话进入"幽灵态"；本机 WPS 11.1.0.10009 复现稳定 | Word 导出改为 **WPS COM 优先，未落盘则 python-docx 本地兜底**（返回值里 `engine` 字段会写明用了哪条），保证交付物一定产出 |
| 6 | 改 `scripts/wps-com.ps1` 后 PowerShell **语法报错** | PowerShell 5.1 对**无 BOM** 的 UTF-8 按 GBK 解析中文注释 | 补丁脚本写回时强制 `UTF8Encoding($true)`（带 BOM），并加 `Parser::ParseFile` 语法自检 |
| 7 | 安装脚本中文全是乱码（`.cmd`） | `.cmd` 在中文 Windows 上是 GBK；用 UTF-8 存（还带 `chcp 65001`）会打乱 cmd 的解析指针，甚至报 `'cho' is not recognized` | `.cmd` 统一 **GBK + CRLF 且不加 chcp**；`.ps1` 统一 **UTF-8 带 BOM** |
| 8 | 目录选择器一打开就报「路径不在允许范围」 | `_drives()` 写死 `"CDEF"`，API 默认路径是 `D:/hermes`（本机无 D 盘该目录） | 改全盘探测（C–Z）+ 默认回落到 `content/plans` |
| 9 | `npm ci` 之后 `mcp` 客户端装错版本，edu-math 工具数变 0 | `mcp` 2.x 移除了 `mcp.server.fastmcp` | `requirements.txt` 固定 `mcp>=1.2,<2` |
| 10 | GitHub 克隆/推送时断时续（`502`、`Failed to connect ... 443`） | 本机 `hosts` 把 `github.com` 指到 `127.0.0.1`，靠本地加速器（Watt Toolkit/Steam++）转发；加速器没开就直连失败 | 开加速器即可；`502` 是瞬时抖动，重试即可 |

## 5. 证据（都在 `tools/wps_spike/evidence/`）

| 文件 | 内容 |
|---|---|
| `01-setup-from-zero.log` | **从零安装全过程的原始输出**：克隆 → `npm ci`（434 包）→ `tsc` 构建 → 写配置（含 commit 号） |
| `02-mcp-handshake.log` | **MCP 服务启动日志原文** + stdio JSON-RPC 原文（initialize / tools/list / tools/call ping）+ 服务自身日志（`Registered 238 professional tools`、`Returning 250 tools`、`ping - SUCCESS (1844ms)`） |
| `03-wps-word-export-*.png` | **WPS 文字窗口截图**（1707×1019），画面里是导出的教案，底部叠加采集时间戳 `2026-09-11 21:33:25` |
| `03-wps-word-export-ocr.txt` | 对上面截图的 OCR 校验（Windows 内置 OCR，zh-Hans-CN）：识别出 `3.3 幂函数`、`一、教案`、`共 3 个环节 40 分钟`、`1. 情境导入（5 分钟）`、`回顾指数函数` 等，证明截图里确实是我方写入的内容而非空白窗口 |

> 说明：截图带时间戳是为了满足"带时间的截图"要求；OCR 校验是我额外加的，因为评审者（和我自己）都
> 无法从文件大小判断截图是否真的显示了内容。

## 6. 一句话风险（换台机器最容易卡在哪）

**WPS 的 COM 行为随会话状态漂移**：同一台机器、同一版本，多次强杀 WPS 或删掉它正打开的目录后，
Writer/Presentation 的 COM 会进入"报成功但不落盘"的幽灵态（坑 #4/#5）。
所以本适配层的设计是「**WPS COM 优先 + 本地生成兜底**」——换台机器复现时，
先用 `02` 那条命令确认 250 个工具能列出来（证明 MCP 通了），
再用 `EDU_TEST_WPS=1` 跑真·WPS 用例（证明 COM 这条路在你机器上是否可用）。
即使 COM 不可用，导出物依然一定产出，只是 `engine` 字段会显示 `python-docx`。
