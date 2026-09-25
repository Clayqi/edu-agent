# PPT 优化（一期 · v1.15.0）

**在右侧侧边面板里读入一份已有的 `.pptx`：先体检 → 再决定改不改 → 改完逐页校验内容没被改动 → 下载新文件。**
原稿从头到尾只读；产物另存，绝不覆盖老师的稿。

> 计划与判定（为什么选 ppt-master、五个候选怎么比的）见 `docs/19-边框里的PPT优化计划书.md`；
> 面板与四页签见 `docs/14-会话内文档预览.md`。本文讲**落地后怎么用、怎么排错**。

---

## 1. 一句话能力边界（先看这个）

| 能做（一期，确定性） | 不能做（二期/别的工具） |
|---|---|
| 拆包**体检**：页数 / 画布 / 主题字体（含中文字体）/ 字号层级 / 表格·图表·图示·图片计数 / **逐页台账**（页型、文字块、字符数、密度异常） | ❌ 不"整套重排/美化"（那是模型逐页手写 SVG 的活，见 §6） |
| **保守原地统一**：统一字体（含 `<a:ea>` 中文字体）/ 统一字号层级 / 清理动画与转场 | ❌ 不合并、不拆页、不改页序、不动文字内容 |
| **内容零丢失校验**：逐页逐串检查原内容还在不在，缺一个就判失败 | ❌ 不认 PDF/Excel/Word 源（不引入 AGPL 的 PyMuPDF） |
| 直接改**.pptx 原生对象**（不是图片），WPS / PowerPoint 里继续可编辑 | ❌ 不碰 WPS COM（走 python-pptx，与 WPS 开关无关） |

---

## 2. 怎么用

1. **开开关**：设置 → Skill 市场 → **「PPT 优化」**（内置，**默认关**）；
2. 右侧侧边面板 → **「文档」** 圆钮 → **【幻灯片】** 页签 → 顶部「PPT 优化」区；
3. 点 **【导入 .pptx】**（或面板标题栏的【导入】，会自动分流）→ 出**体检报告**：
   文件 / 规模（页数·字数）/ 画布 / 主题字体 / 字号层级 / 对象计数 / 需留意（稀疏页·密集页·待确认）；
4. **勾动作**（默认只勾「统一字体」——最保守）→ **【一键优化】**；
5. 结果行给出「改了什么」+ **内容校验**结论（`✅ 逐页逐串都在`）→ **【下载优化稿】**（落 `data/ppt_out/`）。

![流程] 导入 → 体检 → 勾动作 → 一键优化 → 校验 → 下载

---

## 3. 三个动作分别改了什么

| 动作 | 做法 | 风险 / 说明 |
|---|---|---|
| **统一字体** | 遍历每页每个 run（含表格单元格），西文设 `latin`、中文补 `<a:ea typeface>`（python-pptx 不直接管东亚字体，要写 XML） | 默认目标：中文 **微软雅黑** / 西文 **Calibri**；只改字体名，不动字号与颜色 |
| **统一字号层级** | 把 deck 里散落的字号**归并到最近的层级锚**（默认锚 44/32/28/24/20/18/16/14/12），保留相对层级，不做等比缩放 | 容差 0.6pt（只吃浮点噪声）；差 1pt 会真的归并 —— 容差写 1.0 时 23pt 不会并到 24pt（本项目实测踩过） |
| **清理动画 / 转场** | 删每页 XML 的 `<p:timing>`（动画）与 `<p:transition>`（切页效果） | 一次性、不可逆（原稿仍只读，随时可重新导入） |

**体检报告的字段从哪来**：`ppt-master` 的 `pptx_intake.py`（拆包 → `source_profile.json` / `*.slide_library.json` / `*.identity.json`）
+ `beautify_inventory.py`（逐页台账 `beautify_inventory.json`）。我们只做**提炼**，不重写它们的解析。

---

## 4. 原稿只读 / 中间文件在哪（照实说）

| 位置 | 内容 | 生命周期 |
|---|---|---|
| `data/tmp/ppt_jobs/<job_id>/source.pptx` | 上传原稿的**副本**（原文件从不打开写） | 任务目录，默认 24h 后清理（`ppt_polish.cleanup_stale()`） |
| `data/tmp/ppt_jobs/<job_id>/analysis/` | 体检产物（`source_profile.json` 等） | 同上；`--verify` 校验要用它 |
| `data/tmp/ppt_jobs/<job_id>/polished.pptx` | 优化结果 | 同上；点【下载】才复制出去 |
| `data/ppt_out/优化_<job_id>.pptx` | 你下载过的成品（留着，方便再找） | 不自动删 |
| `content/plans/` | **一个字都不写**（单测锁住） | — |

---

## 5. 接口（都在后端一层收口）

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/ppt/status` | **不设门禁**：面板靠它决定按钮灰不灰。返回 `enabled` / `ready` / 安装自检（脚本、依赖、commit）/ 动作清单 |
| `POST` | `/api/ppt/intake` | 上传 `.pptx`（multipart）→ 落任务目录 → 体检报告 |
| `POST` | `/api/ppt/polish` | `{job_id, actions[], target_ea?, target_latin?, size_anchors?}` → 优化 + **自动跑内容校验** |
| `POST` | `/api/ppt/cancel` | 删任务目录（源稿副本 + 中间产物） |
| `GET` | `/api/ppt/download?job_id=` | 复制到 `data/ppt_out/` 后回传 |

**门禁三档**：开关关 → `403 {gate:"capability"}`；没装 → `424 {gate:"install", hint:"跑 deploy/setup_ppt_master.cmd"}`；都过才干活。
`GET /api/mcp/status` 与 `/api/capabilities` 都带 **`ppt_polish_ready`**。

---

## 6. 二期是什么（以及为什么一期不做）

`ppt-master` 的 `workflows/profiles/beautify-pptx.md` 才是"**美化**"：文字逐字冻结、1:1 页数，
**版式整套用 SVG 管线重做**，图表表格按数据重新生成 —— 但那是**模型逐页手写 SVG** 的活，
它自己推荐的模型是 Kimi K3 / Claude（~1M 上下文）；我们默认模型喂不饱，硬上只会产出更差的稿。
所以二期要先把"强模型 + 长上下文"这条准备好，再走它的 beautify 档（那时它的 `--verify` 正好当验收闸门）。

---

## 7. 排错

| 现象 | 原因 / 处理 |
|---|---|
| 面板里看不到「PPT 优化」区 | 该区在**「文档」视图 → 【幻灯片】页签**顶部；先确认在正确的页签 |
| 状态行写「『PPT 优化』已关闭」 | 去 **设置 → Skill 市场 → PPT 优化** 打开（内置能力，默认关） |
| 状态行写「ppt-master 未就绪」 | 跑 `deploy\setup_ppt_master.cmd`；或设环境变量 `PPT_MASTER_HOME` 指向已装目录 |
| 点了【导入】选完文件没反应 | 已修（隐藏 input 的 `change` 绑定曾随视图重建被删）。若再遇到，看控制台是否有 JS 报错 |
| 【一键优化】报 403 / 424 | 403 = 开关关了；424 = ppt-master 没装（响应里带 `hint`） |
| 下载的稿打不开 / WPS 提示修复 | **应该不会**：我们只改字体名、字号与删动画节点，不重写包结构。真遇到请留原稿与产物，这是要立刻查的回归 |
| 优化后文字变了？ | 不会 —— 内容由 `--verify` 逐页逐串把关，失败会明确报出来；报告里也会给"多出来的字符数" |
| 想再改回原样 | 重新导入原稿即可（原稿永远只读，任务目录里的副本 24h 后自动清） |
| 中间文件占地方 | 面板【取消】或等 24h；也可手工删 `data/tmp/ppt_jobs/*` |

---

## 8. 验收怎么跑

```bash
# 1) 后端离线单测（22 例，不联网、不需要真装 ppt-master）
.venv/Scripts/python.exe -m unittest tests.test_ppt_polish -v

# 2) 全量
.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"     # 239 例 OK

# 3) 真机一遍（需要 5174 在跑）
cd tools/uicheck && npm i jsdom && node panel_check.js                    # 23 项检查
```

```bash
# 4) 真机验收（一条命令：体检 → 优化 → 内容校验 → 包深检 → WPS 真打开 → 不碰 content/plans）
.venv/Scripts/python.exe tools/ppt_acceptance.py --with-wps
```

**2026-09-24 实跑记录（14/14 全过）**，源文件 = `content/plans/完整课时模板（默认）.pptx`（11 页 / 1310 字）：

| 步骤 | 结果 |
|---|---|
| [0] 安装自检 | ✅ ppt-master 就绪 `commit=481e057` |
| [1] 体检 | ✅ 11 页 · 1310 字 · 主题字体 宋体/宋体 · 字号层级 32/28/24/20 · 稀疏页 [2,4,6,7,8] · 密集页 [5] |
| [2] 优化 | ✅ 统一字体 **42 个 run**（`target_ea=微软雅黑` / `target_latin=Calibri`）；字号层级 changed=0（原稿字号本就在锚点上）；清动画 0（原稿没有动画） |
| [3] 内容零丢失校验 | ✅ `[VERIFY] passed: every frozen string is present on its page` |
| [4] 包完整性深检（独立核查） | ✅ zip `testzip` 无坏项 · 必要部件齐全 · 11 个 slide 部件 · 页数一致 · **文字多重集与源稿一致（42 段 / 42 段）** · 西文字体已统一为 Calibri · **中文字体写进 `<a:ea>` 42 处** · 无 `<p:timing` |
| [5] **WPS 真打开** | ✅ 经 wps-office MCP 调 `wps_ppt_open_presentation` → **「演示文稿打开成功！」**（包坏了这一步会失败） |
| [6] 没碰 `content/plans` | ✅ 前后目录清单一致（16 项） |

> 人工还需看一眼的（机器验不了）：WPS 里**没有"需要修复"弹窗**、母版还在、
> **每个元素仍可单独选中编辑**、未勾的动作确实没被动。产物：任务目录 `polished.pptx` + `data/ppt_out/优化_*.pptx`。
