# 「边框里的 PPT 优化」接入计划书（v1.15.0 拟）

> 需求原话：「判断哪个 skill 合适我的**边框里的 ppt 优化**，并制定计划书」。
> 「边框」= 会话页右侧的**侧边面板 `aside#sidePanel`**（`docs/14`§2 的「文档」视图，含【文档 / Markdown / 幻灯片 / 结构】四个页签）。
> 「PPT 优化」= 把**已经做好的 .pptx**（老师的答辩 / 说课 / 汇报稿，或我们自己生成的稿）在面板里**体检 → 美化 → 导出**，
> 要求产出**仍可在 WPS / PowerPoint 里逐元素编辑**，不是一张张图片。
>
> 本文只写**计划**，不动代码。文末 §13 有三个需要你拍板的选择。

---

> **后续迭代（2026-09-24）**：老师要的主路径不是"导入旧稿→优化→下载"，而是
> **幻灯片页签本身可编辑 + 默认就好看的排版 + 可导入模板 + 会话内容替换模板文字** →
> 那部分另立计划书 `docs/21-幻灯片编辑与模板计划书.md`。
> 本文这条链路（体检 / 保守原地统一 / 内容校验）**能力一行不减**，
> 但入口按最新决定**从「幻灯片」页签顶部挪到「文档」页签底部的可折叠"高级"区**（详见 19 号 §6）。

## 0. 结论先行

| 问题 | 结论 |
|---|---|
| 选哪个？ | **主选 `hugohe3/ppt-master`（MIT · Python-only）** —— 五个候选里**唯一**同时满足「读已有 .pptx」「母版/版式级的全局美化」「非破坏性（未改动页逐字节保留）」「原生可编辑 DrawingML 输出」四条硬要求的 |
| 要照搬它吗？ | **不要整套照搬**。它是**给强模型（Kimi K3 / Claude，~1M 上下文）用的 skill 工作流**；我们只取它的**确定性脚本链**（§4.1 的「一期」），AI 只做「说什么、改哪页」的决策 |
| 其他四个怎么用？ | `anthropics/skills` 当**规范参考**（SKILL.md / python-pptx 读写范式）；`guizang-ppt-skill` 只借**版式与校验清单**做"从零生成"的视觉基线；`dashi-ppt-skill`（AGPL）与 `GordenPPTSkill`（**明确禁止商用**）**只可参考思路，不得并入产品或仓库** |
| 最大风险 | ① 我们的模型（`deepseek-v4-flash`）比它推荐的弱一个量级 → 一期**只做不依赖模型的确定性优化**；② 优化必然产生中间文件 → 需要给"预览不落盘"红线开一个**受控例外**（`data/tmp/ppt_jobs/`，见 §8） |
| 开工实测（2026-09-23） | 已装 `481e057e` 并跑通三件确定性工具；**修正**：它的 beautify 是"模型驱动的 SVG 重排"，所以一期改划为 **体检 + 内容零丢失校验 + 我们自己写的保守原地统一**，真重排排到二期（详见 §4.1.1） |

---

## 1. 五个候选逐项判定

| 候选 | 关键事实（已核实） | 许可证 | 能读旧 pptx？ | 与我们的匹配 | 判定 |
|---|---|---|---|---|---|
| **ppt-master**<br>`hugohe3/ppt-master` | 产出**原生 DrawingML**（真母版/版式继承、原生形状/连接线/图表/表格、OMML 公式、备注/动画/旁白）；三条附加路线：**从参考稿蒸馏模板**、**把新内容填进已有 .pptx 且保留设计**、**给成品加转场/动画/旁白**；`skills/ppt-master/scripts/` 是**确定性 CLI**（`pptx_intake.py` / `pptx_to_svg.py` / `pptx_template_import.py` / `svg_quality_checker.py` / `pptx_transitions.py` / `pptx_animations.py` / `svg_to_pptx.py` / `pptx_delivery_check.py`）；`pptx_to_svg.py` 还会写出 `animations.json`；MIT；Python 3.10+ 即可（其余依赖一条 `pip install -r requirements.txt`）；Windows 有专门安装文档（PATH / 执行策略） | **MIT** ✅ | ✅ **可以**（"Edit Native PPTX owns source-preserving existing-deck edits"，未改动页**逐字节保留**） | 我们已有 `python-pptx`、有 WPS、有 `pptx_native` 导出、有面板与能力开关 —— 同构度最高 | **主选** |
| anthropics/skills | Claude 官方 skill 规范；含 `pptx` 子技能（python-pptx 级读写、排版检查规则） | 官方仓库 | 部分（OOXML 读写原语） | 不是"美化器"，但**规范与范式**可直接抄 | **参考** |
| guizang-ppt-skill<br>（归藏 PPT） | 单文件 HTML 幻灯片（瑞士网格 / 杂志风），可导出 pptx；**不能读已有 pptx**，只能从大纲新建 | 见仓库 | ❌ | 视觉基线优秀，但**解决不了"优化已有 PPT"** | **只借版式/校验清单** |
| dashi-ppt-skill | HTML 预览 + 一键导出 pptx；上千套版式；浏览器可视化微调；**不能读旧 pptx** | **AGPL-3.0** ❌ | ❌ | AGPL 进产品有传染风险；且同样不能读旧文件 | **不采用**（可人工借鉴版式分类思路） |
| GordenPPTSkill | 21 套中文模板；**只换文字、不动排版**（非破坏性）；出框检测 + 同级字号一致校验；渲染预览依赖 **LibreOffice + pdftoppm**；**首次使用强制联网自更新**；**明确「仅供个人学习研究，严禁任何商业用途」** | **非商用** ❌ | 只读"当模板用"，不做全局美化 | 许可与依赖两处硬伤 | **不采用** |

> 说明：星标数我没有独立核实（本机 `github.com` 被 hosts 指到 127.0.0.1、加速器当前又没起，只能经 jsDelivr 取文件），
> 所以判断一律基于**能力 / 许可证 / 依赖**这三件事，不基于热度。

---

## 2. 我们的现状（可复用的部分）

| 已有 | 位置 | 这次怎么用 |
|---|---|---|
| Python 3.13 venv + `python-pptx` / `python-docx` 已在 `requirements.txt` | `.venv/`、`requirements.txt` | ppt-master 的依赖能直接装进来（§6） |
| 本地 pptx 生成：`pptx_native()` / `pptx_from_rich()` | `src/edu_agent/wps_export.py` | 一期不动它；优化走**新链路**（§4） |
| 导出落盘：`POST /api/wps/export` → WPS MCP / 本地 | `web_server.py:1148` | 保持原样；优化结果的下载走**新端点**（§4.3） |
| 面板（侧边面板「文档」视图）：四页签、可编辑、16:9 预览台 | `static/index.html`（`spRenderDoc()`） | PPT 优化的**入口、进度、结果报告**都加在这里 |
| 面板导入只收 `.docx` | `#docPanelFile accept=".docx"` | 扩成 `.docx,.pptx`，按类型分流（§4.2） |
| 能力开关（MCP + Skill 共用一份状态） | `src/edu_agent/capabilities.py`、`data/capabilities.json` | 新增 skill **`ppt-polish`**（§7） |
| 模板库（导入的 .docx → 富结构） | `/api/template/import` | 二期"套模板"与它并列，不混用 |

**必须守的红线**（`docs/16` §0/§12）：

1. 预览链路**不落盘、不调 WPS**（本次要给"优化任务"开**受控例外**，见 §8）；
2. `wps_export.py` / `/api/wps/export` / `/api/wps/download` / WPS MCP 白名单**行为不变**；
3. 面板外壳与既有页签**只增不改**：加"优化"入口与结果区，不推倒重来；
4. 第三方工具**装在仓库外**（与 `wps-skills` 同策略：`%LOCALAPPDATA%\edu-agent\deps\`），仓库里只放安装脚本与文档。

---

## 3. 目标 / 非目标

**目标（一期必达）**

1. 面板里能**导入一份 .pptx**（老师自己的稿，或我们导出的稿），看到**逐页缩略图 + 体检报告**；
2. 能执行**确定性美化**（不依赖模型）：统一字体与字号层级、统一配色到一套主题、清理动画/转场、修正出框与占位符残留、补页码；
3. **非破坏性**：未选中的页原样保留；输出**原生可编辑** `.pptx`，WPS 里能继续改；
4. 全程可解释：给出「改了哪些页、每页改了什么、哪些没敢动」的报告；
5. 离线单测覆盖，不联网、不调模型也能验。

**非目标（明确不做）**

- 不做"AI 重新设计整套视觉"（一期）；不做旁白/配音（`notes_to_audio`）；不做 PDF/Excel 全书转换（避开 PyMuPDF 的 AGPL，§10）；
- 不用 `guizang` / `dashi` / `Gorden` 的任何代码或模板素材进仓库；
- 不动教案中心的编排台链路（那里的 PPT 生成与导出照旧）。

---

## 4. 方案

### 4.1 三条路线（按依赖模型的多少排序，一期只做第一条）

| 路线 | 干什么 | 依赖模型？ | 用 ppt-master 的哪些脚本 | 期次 |
|---|---|---|---|---|
| **A. 体检 + 确定性美化** | 拆开 .pptx → 统计（页数/母版数/版式数/字体与字号清单/颜色清单/动画与转场条数/疑似出框/空占位符/图片分辨率）→ 按规则统一（字体、字号层级、主题色、清动画、去占位残留、补页码）→ 重新打包导出 | **不依赖** | `pptx_intake.py`、`pptx_to_svg.py`（含 `animations.json`）、`pptx_transitions.py`、`pptx_animations.py`、`svg_quality_checker.py`、`svg_to_pptx.py`、`pptx_delivery_check.py` | **一期** |
| **B. 套模板 / 换内容** | ① 把老师的品牌稿或学校模板**蒸馏成模板**（母版/版式/文本槽）；② 把会话里这份教案**填进**该模板；③ 只替换文字、保留版式 | 轻（选页与措辞） | `pptx_template_import.py`、`mirror_template_materialize.py`、`svg_authoring_view.py`、`page_plan.json` 选页/换序 | 二期 |
| **C. AI 设计决策** | 让模型读完整套稿，输出"叙事/版式/配图"改造方案再执行 | 重（需强模型 + 大上下文） | 全套 workflow（`SKILL.md` + `workflows/*`） | 三期（可选，接外部强模型） |

> 关键判断：**一期把"能确定性做对的事"做扎实，比接一个我们喂不饱的强工作流更有价值。**
> ppt-master 自己也写明「工具只承担流程，模型决定上限」——我们一期就不碰上限那部分。


### 4.1.1 开工实测修正（2026-09-23，已装 ppt-master `481e057e`）

**实测发现（改变了 §4.1 的假设，按事实改）**：

| 以为 | 实际 |
|---|---|
| ppt-master 的 beautify 是"原地统一字体/配色/清动画"的补丁式优化 | **不是**。`workflows/profiles/beautify-pptx.md` 明确：**"不是补丁、不是填充"** —— 它把原稿**文字逐字冻结**（1:1 页数/页序），然后**用 SVG 管线把版式整套重做**，产出**新的原生 pptx**；且明确"**图表/表格按数据重新生成，不逐字节搬运**" |
| 它有一批确定性脚本可直接当"美化引擎" | 它的**确定性**能力集中在这几件（都不需要模型）：`pptx_intake.py`（拆包体检）、`beautify_inventory.py`（逐页台账 + `--summary/--page`）与 **`--verify <export.pptx>`（内容零丢失校验，缺一个串就 exit 1）**、`beautify_identity.py`（主题/字体/字号/画布）、`pptx_to_svg.py`（视觉参考包）、`svg_quality_checker.py`（出框/字号校验）。**"重排"本身是模型逐页手写 SVG 的活** |
| 它的 `usage_contract` 里 `beautify` = 原地保留 | `beautify` 档的语义是：**把源稿的文字/页序/页数/配色/字体/字号提升为"锁定约束"**（经用户确认后），再重排 |

**因此一期改划（不变的：入口、开关、落盘策略、验证方式）**：

| 项 | 一期做什么 | 谁来做 |
|---|---|---|
| **体检报告** | 拆包 → 页数/画布/主题字体（含中文字体 `Hans`）/主题字号与层级/实际出现的字体与字号/表格·图表·图示·图片计数/**逐页台账**（页型、文字块数、字符数、密度异常） | ppt-master 的 `pptx_intake.py` + `beautify_inventory.py`（确定性） |
| **内容零丢失校验** | 任何改稿之后跑 `--verify`：逐字检查每个原串还在不在它那一页，并报"多出来的字符数"（>0 = 违规加字） | 同上（确定性） |
| **保守原地统一** | `统一字体`（含 `<a:ea>` 中文字体）、`统一字号层级`（把散落字号归并到层级锚）、`清理动画/转场`（删 slide XML 的 `p:timing` / `p:transition`） | **我们自己用 python-pptx 写**（ppt-master 不做这个；它只做重排） |
| **整套重排（真"美化"）** | 走它的 beautify 档：文字冻结 + SVG 重排 + 原生导出；**需要强模型逐页手写 SVG** | **二期**（要接强模型；我们的默认模型喂不饱） |

**结论**：一期 = **"体检 + 校验 + 保守原地统一"**（全部确定性与可控，不赌模型）；
二期 = 接强模型走它的 beautify 档做**真重排**（届时它的 `--verify` 正好当我们"内容没被改坏"的验收闸门）。
这样一期就能交付价值，也把"改坏老师稿子"的风险压到最低（原地动作都可 dry-run、可只体检不改）。

### 4.2 面板交互（加在现有「文档」视图里，不新开界面）

```
侧边面板 → 「文档」视图 → 【幻灯片】页签
├─ 顶部：[导入 .pptx]  [体检]  [一键美化]  [下载优化稿]
├─ 体检报告卡：页数 / 母版 / 字体清单（含未嵌入字体标红）/ 字号层级 / 动画与转场条数 /
│              疑似出框 N 处 / 空占位符 M 处 —— 每项可展开看"第几页"
└─ 逐页缩略图（复用现有 16:9 预览台；点某页 → 右侧显示该页体检明细与"建议动作"）
```

- **导入分流**：`#docPanelFile` 的 `accept` 扩成 `.docx,.pptx`；`.docx` 走现有 `/api/template/import`，`.pptx` 走新的 `/api/ppt/intake`；
- 优化是**长任务**（几十页可能几十秒）：沿用现有 SSE 思路，面板给**进度条 + 可取消**，完成后把结果 `.pptx` 交给现有【下载▾】出口；
- 结果区（`#docPanelRes`）追加一行「优化报告」：`已统一字体 3 种→1 种 · 清掉动画 42 条 · 修正出框 7 处 · 未改动 12 页`。

### 4.3 接口（新增，全部在后端一层收口）

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/ppt/status` | ppt-master 是否就绪：安装路径、版本、脚本清单、Python 依赖自检（缺什么列什么）。前端据此决定"优化"按钮可不可点 |
| `POST` | `/api/ppt/intake` | 上传 `.pptx` → 落**任务临时目录** → 跑 `pptx_intake/pptx_to_svg` → 返回**体检报告 JSON**（不做任何修改） |
| `POST` | `/api/ppt/polish` | 入参：`{job_id, actions:["font","type-scale","palette","strip-anim","fix-overflow","page-number"], pages:"all"|[…]}`；返回 `task_id`，进度走 SSE |
| `GET` | `/api/ppt/progress/{task_id}` | 进度 / 阶段 / 当前页 / 可取消 |
| `POST` | `/api/ppt/cancel` | 取消任务并清理临时目录 |
| `GET` | `/api/ppt/download?job_id=` | 下载**优化后**的 `.pptx`（与 `/api/wps/download` 并列，互不影响） |
| `POST` | `/api/ppt/preview` | 某页 PNG/SVG 预览（给缩略图用；不落盘到 `content/`，走临时目录 + 内存缓存） |

**与现有链路的关系**：`/api/wps/export`（我们的稿 → 落盘）与 `/api/ppt/*`（别人的稿 → 优化 → 落盘）是**两条独立链路**；
前者一行不改，后者失败也不影响前者。

---

## 5. 为什么"读旧 PPT 美化"只能选 ppt-master（判定依据）

1. **只有它读**：其余四个要么只能从大纲新建（guizang / dashi），要么只把旧稿当"模板"换文字（Gorden），没有"分析整套旧稿 → 全局统一"的能力；
2. **只有它做到母版/版式层**：`pptx_template_import.py` 保留 Master/Layout 继承链与文本槽，`pptx_to_svg.py` 连动画/转场都读得回来（写 `animations.json`）——这正是"统一母版、清理动画"的实现基础；
3. **只有它保证非破坏**：未改动页**逐字节保留**（README 的 Edit Native PPTX 契约），这对老师"我就想美化几页、别动我的内容"是决定性的；
4. **只有它的许可能用**：MIT；Gorden 明确禁商用，dashi 是 AGPL；
5. **只有它和我们的栈同构**：Python-only、CLI 确定性脚本、不需要装 Office 插件、不需要 LibreOffice 渲染。

---

## 6. 安装与依赖（照 `wps-skills` 的既有做法）

```cmd
:: deploy\setup_ppt_master.cmd（新增，一次性）
:: 1) 仓库外安装目录（与 wps-skills 同策略，不进仓库）
set DEST=%LOCALAPPDATA%\edu-agent\deps\ppt-master
:: 2) 克隆走 gh-proxy（本机 github.com 被 hosts 指向 127.0.0.1，直连不可用；该项目此前实测 gh-proxy 约 10MB/s）
git clone https://gh-proxy.com/https://github.com/hugohe3/ppt-master.git "%DEST%"
:: 3) 依赖走国内镜像（venv 已装 python-pptx / python-docx，只会补差量）
"%DEST%\..\..\..\..\edu-agent3\.venv\Scripts\python.exe" -m pip install -r "%DEST%\requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
:: 4) 自检：脚本在不在、版本号、依赖全不全（对应 /api/ppt/status）
"%DEST%\...\python.exe" "%DEST%\skills\ppt-master\scripts\pptx_intake.py" --help
```

- **版本钉住**：记录 clone 到的 commit SHA 进 `data/ppt_master.json`（形态照 `data/wps_mcp.json`），`/api/ppt/status` 报出来；升级只走 `update_repo.py` 或重新 clone；
- **不引入**：PyMuPDF（AGPL，只有 PDF 源才需要）→ 一期不接 PDF 输入；`notes_to_audio`（TTS）不接；
- Windows 注意：ppt-master 有**执行策略 / PATH**要求，安装脚本里显式检查并给出中文提示。

---

## 7. 能力开关与 UI 门禁

- 新增 skill **`ppt-polish`**（名称「PPT 优化」，`builtin: true`，默认**关**）—— 与 `doc-session-preview` 同机制：
  关掉时面板不显示"优化"入口、`/api/ppt/*` 除 `status` 外一律 403 并说明原因；
- `GET /api/mcp/status` 与 `/api/capabilities` 各加一个字段 **`ppt_polish_ready`**（= skill 开关 ∧ 安装自检通过）；
- 「优化」按钮三态：可用 / 灰显（未安装，tooltip 给安装命令）/ 灰显（开关关闭）。

---

## 8. 落盘策略（给红线开一个受控例外，写清楚）

| 目录 | 用途 | 生命周期 |
|---|---|---|
| `data/tmp/ppt_jobs/<job_id>/` | 上传的原稿、解包中间件、SVG 中间件、优化稿 | 任务结束或取消即删；启动时清理超过 24h 的残留 |
| `data/ppt_out/` | 用户点【下载】后**保留**的优化稿（可在设置里改到与教案共用目录） | 与 `content/plans/` 同样的用户可见产物，**不自动删** |
| `content/plans/` | **不动**（现有导出链路的地盘） | — |

- 体检报告与缩略图**只走内存 + 任务目录**，不写 `content/`；
- 面板上明示「优化会在任务目录产生中间文件，完成后自动清理」——**不装作无痕**。

---

## 9. 测试与验收

**离线单测**（`tests/test_ppt_polish.py`，不联网、不调模型、不依赖真安装）：

1. `status` 在"未安装 / 已安装 / 脚本缺失"三种情形下的返回与 `ppt_polish_ready` 计算；
2. 能力开关：关掉 → `/api/ppt/*` 403 但 `/api/wps/export` 行为不变（**双向解耦**，与 `TestSessionDocPreview` 同款）；
3. 删除动作清单 → 命令行参数拼装正确（`--dry-run` 可断言）；
4. 任务目录：创建/取消/超时清理，断言不碰 `content/plans/`；
5. 报告 JSON 结构稳定（前端依赖它有契约）。

**真机一次**（手工，记为验收证据）：

- 拿一份真 `.pptx`（≥10 页、含动画与两种字体）→ 体检 → 一键美化 → 用 **WPS 打开**：① 能正常打开无修复提示；② 母版/版式仍在；③ 未选中的页内容未变；④ 字体与字号层级统一；⑤ 动画已清；⑥ 每个元素仍可单独选中编辑。

**面板交互**：导入 `.pptx` → 报告出现 → 勾选动作 → 进度 → 结果行 → 下载并打开（与 `docs/16` §11 的测试写法一致，补进 `docs/14` 的排错表）。

---

## 10. 风险与回退

| 风险 | 影响 | 对策 |
|---|---|---|
| **模型能力不足**（推荐 Kimi K3/Claude；我们默认 `deepseek-v4-flash`） | 路线 C 做不好 | 一期只做路线 A（确定性）；C 作为三期可选，允许接外部强模型 |
| ppt-master 体量大（skill 包 ~56MB 起） | 安装慢、占空间 | 装仓库外；`/api/ppt/status` 自检；失败不影响其它功能 |
| 网络：`github.com` 被 hosts 指向 127.0.0.1，加速器当前未启 | 装不上 | 走 `gh-proxy.com`（本项目已实测可用）+ pip 国内镜像；安装脚本失败时给**逐条中文指引** |
| Windows 执行策略 / PATH | 脚本跑不起来 | 安装脚本显式检查（ppt-master 官方也要求这步） |
| **AGPL 组件（PyMuPDF）** | 许可证污染 | 一期不接 PDF 输入；如将来要接，单独隔离进程 + 分发时剔除（README 亦如此建议） |
| 中间文件残留 | 磁盘涨、隐私 | 任务目录按 job 隔离 + 24h 清理 + 明示；**不写 `content/`** |
| 优化改坏了老师的稿 | 信任损失 | 原稿**只读**、产物另存；所有动作可**dry-run**先出报告；一页都不改也能退出（只体检不美化） |

---

## 11. 分期

| 期 | 内容 | 交付判定 |
|---|---|---|
| **一期** | 安装自检 + 导入 .pptx + 体检报告 + 确定性美化（字体/字号层级/主题色/清动画/修出框/页码）+ 下载；skill `ppt-polish` 开关 | 离线单测全绿 + WPS 真机打开无异常 + 面板跑通一遍 |
| **二期** | 套模板（老师品牌稿 → 模板）与"内容填进模板"；选页/换序；演讲备注 | 用一份真品牌稿跑通并保留母版 |
| **三期（可选）** | 接强模型做叙事/版式/配图决策（路线 C）；必要时借 `guizang` 的**校验清单**做视觉基线（不引代码） | 产出与手工稿对比评估 |

---

## 12. 交付物清单（对应仓库通行的输出工作流）

| # | 交付物 | 位置（拟） |
|---|---|---|
| 1 | 安装脚本 + 自检 | `deploy/setup_ppt_master.cmd`、`/api/ppt/status` |
| 2 | 后端链路 | `src/edu_agent/ppt_polish.py`（新）、`web_server.py`（新端点） |
| 3 | 前端面板 | `static/index.html`：`spRenderDoc()` 的幻灯片页签加"优化"区；导入 accept 扩 `.pptx` |
| 4 | 能力开关 | `capabilities.py` 注册 `ppt-polish`；`/api/mcp/status` 加 `ppt_polish_ready` |
| 5 | 测试 | `tests/test_ppt_polish.py`（离线） |
| 6 | 文档 | `docs/20-PPT优化.md`（落地说明：怎么用、怎么排错）、`docs/00` 索引、`CHANGELOG` |
| 7 | 证据 | 真机一次的报告 + WPS 打开截图路径 + 单测输出 |

---

## 13. 需要你拍板的三件事

1. **一期范围**：就按 §4.1 路线 A（体检 + 确定性美化）做，还是要我直接把"套模板"（路线 B）一起排进一期？（B 会显著变长）
2. **美化默认动作**：`统一字体 / 统一字号层级 / 统一主题色 / 清理动画 / 修正出框 / 补页码` —— 六项**默认全开**，还是默认只做"体检 + 前两项"（更保守）？
3. **产物目录**：优化稿默认落在 `data/ppt_out/`（我建议），还是直接进 `content/plans/`（与现有导出同一处，便于老师找）？

> 这三条定了我再开工；开工前会先把 §6 的安装脚本跑通（这一步不依赖你的选择）。
