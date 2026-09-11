# edu-agent：课本教练（Agent A）× 教案 Agent（Agent B）× 总指挥（Agent S）

以教材为**唯一事实来源**的高中数学多 Agent 项目（施工版）：
**Agent A 课本教练**（学生答疑）、**Agent B 教案 Agent**（老师备课）与 **Agent S 总指挥**
（监督派单）是相互独立、各自完整的 Agent（独立性红线见 [docs/05-多Agent协作计划书.md](./docs/05-多Agent协作计划书.md) §0），
共用同一只读教材向量库与检索/生成底座；web 网关（5174，唯一 UI）负责意图路由与会话编排。

## 双 Agent 现状（2026-09-07）

| Agent | 身份 / 职责 | 独立入口 | 状态 |
|---|---|---|---|
| A 课本教练 | 高中生教材答疑（prompts.SYSTEM_PROMPT），答案带 [编号]+页码引用 | `generate.ask / ask_turn`；CLI `python src/edu_agent/generate.py "问题"`（--chat 进多轮）；UI 见 api.py | ✅ 已交付（S1~S10 + 工程补强） |
| B 教案 Agent | 老师备课：知识点+教学问题/目标 → 结构化教案（PlanRecord，可带模板） | `planner.make_plan`；CLI `python src/edu_agent/planner.py "知识点" "目标"` | 🟡 代码就绪（M0/M1），UI「教案」页未接入（M3 待施工） |
| 编排层 | LangGraph Router：显式 mode 优先 + 教案意图关键词路由；节点 lazy import + 异常隔离；P1 学情拼接 | `graph.ask / ask_coach / ask_plan`；CLI `python src/edu_agent/graph.py [--plan 知识点 目标] 文本` | ✅ 已就绪（tests/test_graph.py 全绿） |
| 模板认定 | B 的扩展职责：.docx → 板块结构 TemplateSpec → 存档 content/templates/ | `template_spec.recognize_docx / save_template`；CLI `python src/edu_agent/template_spec.py 模板.docx [--save]` | 🟡 代码就绪 + 样例已认定（M0），UI 上传入口未接 |

## 择优修订记录（2026-09-06，自 textbook-coach 采纳）
- **首发教材改为 数学·人教A版2019课标版·必修第一册**（266 页文字层 PDF 已到手，原"物理"仅为无文件时的建议）
- **Embedding 改走本机 Ollama bge-m3**（localhost:11434，免硅基流动 key）；硅基流动留作远程备用 provider
- **LLM DeepSeek**：key 复用 hermes config.yaml 注入 .env；base=https://api.deepseek.com/v1，model=deepseek-v4-flash
- **PDF 自动切节管线**（PyMuPDF 解析目录页 → 按章/节切文本）先行覆盖全册，人工精修细卡作质量天花板
- 向量库维持 **Chroma**（已装好可用）；内容资产纯文本、与向量库选型解耦
- 详规见 content/README.md v3 与 src/edu_agent/pdf_import.py

## 内容双轨
| 轨 | 目录 | kind | 状态 |
|---|---|---|---|
| 人工精修细卡 | content/structured/ | concept/example/exercise | ⏳ S3 第一章施工中（用户决定暂缓） |
| PDF 自动整节 | content/structured_auto/ | section | ✅ 5 章 52 节（151 chunk） |

## 工程补强（2026-09-07）：缺失项 #2/#3/#4 补齐 + 单测全绿
按历史遗留的缺失项清单逐条补齐（对应模块 docstring 各标 #N）：

| 缺失项 | 模块 | 说明 |
|---|---|---|
| #1 引用校验/诚实降级（S8 前置） | grounded.py | validate/degrade 分型（empty/parse_error/low_confidence/out_of_scope），系统失败不伪装"教材没讲" |
| #2 无法多轮追问 | session.py | Conversation 有界轮次 + 指代消解（is_follow_up/resolve_query）+ history_block，generate.ask_turn |
| #3 复现问题靠用户截图 | logsetup.py | 每请求 request_id（contextvars）+ EVENT 结构化单行日志（k=v）+ 可选滚动文件；纯 stdlib、默认静音、幂等 setup |
| #4 结构问法系统性失败 | preprocess.py | 章/节/页/题号坐标解析（阿拉伯+中文数字）+ 教材术语归一（口语→课本用词）+ 结构化 hints，接入 generate 检索回退链 |

一并落地：**生成重试**（默认 3 次逐次升温、退避，最后才降级 parse_error）、**引用规整强化**（幽灵引用清洗、降级回显原问题）、
**编排层 P1**（graph 把 A 的学情摘要 coach_summary 拼入 B 的 goal，B 无摘要照常独立出教案）。

### 单测
`tests/` 全 mock（检索+LLM+节点桩），零网络/零 Chroma/零 LLM。当前 **112 例全绿**（Ran 112 tests OK；一期收口后含新增 store/routing 15 例）：

```
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

| 文件 | 覆盖 |
|---|---|
| test_generate.py | plainify/JSON 解析/重试/降级/幽灵引用/多轮 ask_turn/build_messages |
| test_preprocess.py | 坐标解析（#4）/术语归一/题型分类/结构问法提示 |
| test_session.py | 会话/追问判定/指代合并/历史块/序列化（#2） |
| test_logsetup.py | 请求上下文/幂等/结构化事件（#3） |
| test_grounded.py | 引用校验/降级文案分型 |
| test_graph.py | 路由逻辑/图级路由/节点故障隔离/P1 学情拼接 |
| test_store.py | host.store 会话：CRUD/40条截断/跨实例持久化/旧 JSON 迁移（一期新增） |
| test_routing.py | routing 单一来源：派单决策/显式 mode/接线一致性（一期新增） |

## 结构
```
./  (.env 不入库；.venv 已建，Python 3.11 via uv)
├─ requirements.txt                        # S1 验收：A.DeepSeek B.bge-m3(1024) 全绿 PASS
├─ content/README.md                     # v3 契约（chunk 头行格式/坐标/边界）
│  └─ templates/                          # Agent B 模板存档（orig/ 原件备份 + 认定 .json + _current.json）
├─ data/                                  # 运行数据（会话库/上传/日志；可经 EDU_DATA_DIR 整体外移）
│  ├─ edu_sessions.db                     # 统一会话存储（web_sessions.json 已自动迁移并入）
│  └─ logs/edu_agent.log                  # 滚动事件日志（logsetup）
├─ legacy/                                # 归档（Gradio UI api.py / 临时脚本 / 旧日志），不参与运行
├─ deploy/                                # 启动/停止脚本（start_ui / start_web / stop_ui / run_ui.ps1）
├─ docs/                                  # 文档（00 索引 / 01 架构 / 02 演示剧本 / 03 协作 / 04 部署 / 05 计划书）
├─ eval/                                 # 评测集与存档（golden_questions / s9_results / demo 兜底）
└─ src/edu_agent/
   ├─ config.py            # 读 .env；运行参数收口（rerank/数据目录/日志）；LLM + 双 embedding
   ├─ ollama_embeddings.py # 本地 bge-m3 封装（分批，防 context 超限）
   ├─ routing.py           # 【单一来源】意图路由：教案类→B，其余→A（S/A/网关共用）
   ├─ host/                # 【host 层】进程级基础设施（对照 DSH host 平面）
   │  └─ store.py          # 统一会话持久化（SQLite WAL，按 session_id 键控，旧 JSON 自动迁移）
   ├─ pdf_import.py        # S2.5：PDF 目录页解析 → 整节 md（自动）
   ├─ ingest.py            # S5：两目录 -> Chroma（幂等全量重建；长节按行切块）
   ├─ retrieve.py          # 检索（主节优先 prefer_main / kinds / chapter 过滤 / 可选 rerank）
   ├─ prompts.py           # A/B 两套独立系统提示词 + JSON 指令 + 降级文案分型
   ├─ generate.py          # 【Agent A 本体】ask/ask_stream/ask_turn -> AnswerRecord（含重试/规整）
   ├─ grounded.py          # 引用校验 + 诚实降级
   ├─ session.py           # 多轮会话 Conversation/指代消解（内存态；持久化归 host/store）
   ├─ logsetup.py          # 请求级日志（request_id + EVENT 单行，幂等）
   ├─ preprocess.py        # 查询预处理：坐标/术语/分类
   ├─ planner.py           # 【Agent B 本体】make_plan -> PlanRecord（教案）
   ├─ template_spec.py     # 教案模板认定（.docx -> TemplateSpec）
   ├─ supervisor.py        # 【Agent S 本体】总指挥：拆解→派单 A/B→质检汇总（流式事件）
   ├─ graph.py             # 编排兼容壳：LangGraph Router（CLI/测试；路由词表已收口到 routing）
   ├─ chat.py              # Agent A 多轮 react-agent 壳（CLI 演示；web 多轮走会话存储）
   ├─ plan_html.py         # 教案 markdown -> HTML 落盘（content/plans/）
   ├─ memory.py            # Agent A 长期记忆（SQLite data/memory.db，按 profile）
   ├─ math_verify.py       # 简易验算附加（出错兜底提示）
   ├─ pdf_upload.py        # 用户上传 PDF -> 独立向量库 + 检索
   └─ web_server.py        # 【唯一 UI 网关 5174】薄路由 + SSE（A/S/B/auto + 模板 + PDF）
```

## 进度勾选清单
- [x] S1 基地：依赖装好（3.11）、**双连通冒烟全绿**、骨架就位
- [x] S2.5 教材到手（数学必修一 PDF）+ 自动切节全册（52 节）
- [x] S5 入库 Chroma **151 条**（幂等全量重建）
- [x] S4(节级) eval/golden_questions.json 15 条（细卡版跳过，待精修后升级 chunk 级）
- [x] S6 检索冒烟 **13/15**（>=12 达标；两处❌为第四章旁栏节措辞撞车，记录待调优）
- [x] S7 ask() 合法 JSON + 坐标引用（实测：单调性/集合/正弦函数 3 例高质量作答）
- [x] S8 越界题走降级分支（实测「不定积分」→ 低置信降级，不硬编）
- [x] S9 全量 15 题质检 **15/15 合格**（eval/s9_results.json）
- [x] S10(初) Gradio 问答界面 → 已随一期收口退役（归档 legacy/api_gradio.py，唯一 UI 迁移至 5174）
- [x] S10 演示剧本 docs/02-演示剧本.md + 裸 GPT 对照存档（eval/s10_naked_compare.md）+ 排练第 1 遍（计时）
- [x] 工程补强（2026-09-07）：#2 会话 / #3 日志 / #4 查询预处理 + 重试 + 引用规整；**tests/ 97 例全绿**
- [x] M0 模板认定（代码 + 样例）：content/templates/高中数学_函数的概念_教案.json（源自样例 .docx）
- [x] M2 编排层 graph.py：LangGraph Router + 节点故障隔离 + P1 学情拼接（tests/test_graph.py 全绿）
- [ ] S3 人工精修细卡（用户决定跳过，暂缓）
- [ ] S10(现场) 剧本排练第 2 遍（真人走场）+ 录屏兜底（无录屏时 eval/demo_canned_answers.md 直接兜底）
- [ ] M1/M4 教案 B 端到端验收（3 份样例 + 学情抽检，需真实 DeepSeek）
- [x] M3 UI：Harness 风格聊天页（顶部切 Agent：A 答疑/B 教案/自动 + S 总指挥；模板下拉 + 新建会话；折叠区 .docx 模板认定）→ 现唯一入口 http://127.0.0.1:5174
- [x] 一期架构收口（对齐 DSH，见下节）：**tests/ 112 例全绿**

## 乱码优化与检索调优记录（2026-09-06 下午）
- **语料乱码清洗**（scripts/clean_corpus.py + scripts/repair_fm.py）：全角归一、人教字形替换字母映射（狓→x 犃→A…）、私用区/矢量垃圾行剔除。**注意**：pdf_import.py 重跑后需先跑 repair_fm（补 front-matter）再 clean。
- **检索主节优先**（retrieve.py prefer_main）：编号节硬优先于旁栏（阅读与思考/小结/信息技术应用），S6 由 13/15 → **14/15**。
- **已知弱点**：第四章 4.2 指数函数所在页含表格/图形，抽取文本受污染致向量偏差，检索该节问仍可能落到旁栏（黄金题 Q11 未命中，属公式/表格边界，未死磕）。
- **慢题波动**：DeepSeek 偶发 60~113s（非代码问题），演示只选已验证快题（见 docs/02-演示剧本.md）。

## 一期架构收口（2026-10，对照 DSH DeepSeek Harness 架构）

目标：不改业务正确性，把「一层平铺 + 全局单例 + 逻辑多处复制」收成 DSH 式的
**host / agent / session 分层**（设计细节与对照表见 docs/01-dsh架构对标与一期重构.md）。

| DSH 概念 | 本仓库落点 | 改动 |
|---|---|---|
| host 平面（持久化/注册表/配置收口） | `host/store.py` SessionStore | 会话从 web_server 全局 dict + JSON 覆写 → **SQLite(WAL) 按 session_id 键控**；旧 `web_sessions.json` 首启自动迁移并改名留档 |
| 配置收口（不散落在启动脚本/env 各处） | `config.py` Settings | rerank（RERANK_*）、数据根（EDU_DATA_DIR）、会话库（EDU_SESSIONS_DB）、日志（EDU_LOG_FILE）全部收进 settings；retrieve.py 不再自己读 env |
| 路由/策略单一来源 | `routing.py` | supervisor/graph/web 网关三份漂移关键词表 → 一份 `decide()`；graph.PLAN_HINTS 变为同一对象别名 |
| 网关薄化 | `web_server.py` | 只做静态/参数/分派 + SSE（事件形状不变，前端零改动）；日志默认 data/logs/edu_agent.log + 启动预热移植 |
| 会话层 | `session.py` + store | Conversation（内存多轮）只管理解追问；持久化统一走 host/store |
| UI 合一 | — | Gradio 7860 退役 → `legacy/api_gradio.py` 归档（语音/反馈/修正代码留档可回迁）；所有启动脚本指向 5174 |
| 运行数据与代码分离 | `data/` | 会话库/上传/日志集中；根目录杂项（tmp_*.py、*.log）移入 legacy/ |

验收：`tests/ 112 例全绿`（原 97 + 新增 store/routing 15 例）；5174 全功能冒烟通过。

## 2026-09-10 更新：看原页 / 图片公式防幻觉 / UI 细节

背景：教材里公式与图象是图片、PDF 文字层抽不到（且带损：`750°` 抽成 `750c`、小节号 `5.1.1` 抽成 `511!`），
模型读到半截乱码会"顺手补全" → 幻觉。本轮把「不许编」落成机制，并把原书那一页直接给用户看。

**能力**
| 能力 | 落点 | 说明 |
|---|---|---|
| 片段体检 | `src/edu_agent/figdetect.py` | 给每个片段判 `has_figure` / `fig_nums`(图号) / `fidelity`(文字层是否损坏)；口径与入库回填一致 |
| 元数据回填 | `scripts/backfill_chunk_meta.py` | 给向量库 151 个片段补上述三键（跑前自动整库备份到 `data/backup/`）。实测：有图号 64、低保真 33 |
| 生成侧硬约束 | `src/edu_agent/prompts.py`（FIGURE_GUARD）+ `src/edu_agent/generate.py`（`_snippet_block()`） | 含图片段加 ⚠ 标注并附硬指令：片段文字里没出现的公式/符号**一律当"书上只有图"**，禁止写出/推导/用常识补全，只给页码+图号并提示看原页。非流式与流式两条链路共用同一函数，防口径漂移 |
| 原页图接口 | `GET /api/page_image?page=N[&source=&dpi=]`（`src/edu_agent/page_image.py`） | 印刷页 → 物理页 `+6`；pymupdf 渲染 150dpi PNG，缓存 `data/page_cache/`；越界 404、非法 422 |
| 看原页浏览器（前端） | `static/index.html` | 正文绿色引用 pill 与侧栏引用卡都可点开原书页：上一页/下一页、跳任意页、本节首/本章首、回到引用页、键盘 ←→、Esc |
| 目录页码范围 | `scripts/build_toc_ranges.py` → `content/toc_ranges.json`；`GET /api/textbook/toc` | 回答"这个知识点在哪节、这一章从第几页到第几页"（第三章 p59–p102、3.3 幂函数 p89–p92、全书 p1–p260） |

**UI 细节**：左侧栏可收起（对齐 DeepSeek Harness，品牌行右上角按钮，状态记 localStorage）；左上角面包屑显示当前对话名称（首问后自动命名）；引用随消息持久化（`store.append(meta=)`，刷新/重开会话后绿色 pill 与「复制/重新生成」仍在）；修复右侧面板圆钮标签被下一行圆遮挡、以及 `--ink-800` 变量未定义导致激活态标签白底白字看不见。

**注意**：`src/edu_agent/prompts.py` / `src/edu_agent/generate.py` / `src/edu_agent/web_server.py` 改动需重启 5174；`static/` 前端改完刷新即可。向量库或教材更换后需重跑 `scripts/build_toc_ranges.py`。

## 教案中心 = 教案 × PPT 可视化编排台（2026-09-10 晚）

侧栏「教育能力 → 教案中心」（教师角色）不再进对话，而是打开编排工作台 `#view-design`：

| 区域 | 内容 |
|---|---|
| 顶部 | 课题、学情/课时、生成骨架、＋添加环节、保存、导出 HTML、预览 PPT |
| 左栏「教案结构」 | 每个环节一行：序号 / 名称 / 分钟 / 上移 ↓ / 下移 / 删除；要点文本框（每行一条） |
| 右栏「PPT 幻灯片」 | 每页对应一个环节：缩略图显示标题+要点，底部标注「第 N 页 · X 分钟」；点卡片跳回左侧对应环节 |

两侧由同一份状态驱动，任一侧改动另一侧即时同步；统计（共 N 个环节 · X 分钟）实时更新。
数据自动存 `localStorage: edu_design_v1`；「导出 HTML」产出含教案全文 + PPT 大纲的独立 HTML；「预览 PPT」按 16:9 全屏逐页预览。
侧栏「教育能力」分组也可伸缩（点标题或箭头收起/展开，状态记忆在 `localStorage: edu_cap_open`）。
学生角色下同一入口仍是「AI 答疑」（对话视图）。

## 运行
- **UI（唯一入口，Harness 风格聊天页）**：`deploy/start_web.cmd` / `启动课本教练.bat`（顶层） / `deploy/run_ui.ps1` → http://127.0.0.1:5174（先确保 Ollama bge-m3 在 localhost:11434 运行）；顶部切 Agent A（答疑多轮）/ B（教案）/ S（总指挥派单）/ 自动；B 按当前模板出教案（默认=已认定《函数的概念》模板），含 PDF 上传问答与模板认定；日志滚到 `data/logs/edu_agent.log`
- **Agent A CLI**：`.venv/Scripts/python.exe src/edu_agent/generate.py "怎么判断函数单调性？"`；多轮：`... generate.py --chat`
- **Agent B CLI（出教案）**：`.venv/Scripts/python.exe src/edu_agent/planner.py "函数的单调性" "重点班45分钟"`
- **编排层 CLI**：`.venv/Scripts/python.exe src/edu_agent/graph.py "帮我写一份函数的单调性的教案"`（普通问自动走 A）
- **总指挥 CLI**：`.venv/Scripts/python.exe src/edu_agent/supervisor.py "帮我备一节 对数函数 的教案"`
- **单测**：`.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"`（当前 **112 例全绿**，零网络/零 Chroma/零 LLM）
- 停止：`deploy/stop_ui.cmd`（查杀 5174）或 `netstat -ano | findstr :5174` 后 Stop-Process
- 注意：会话数据现在落 `data/edu_sessions.db`（SQLite），重启不丢；想整体搬数据根设 `EDU_DATA_DIR` 即可
- 已知：个别题端到端偶发 60~113s（DeepSeek 波动），演示选已验证的快题；越界题自动降级
- 公式策略：生成后统一 plainify（generate.plainify_math），输出纯文本/Unicode（⊆ ∈ √ x^2），不再输出 $…$/反斜杠命令——任何环境零乱码；复杂公式给页码翻书兜底

## 📊 会话统计存档

> 底框账本：后续每个施工轮次把会话统计追加到本节，一行一条。

| 轮次 | 统计 |
|---|---|
| 2026-09-06 基地→问答链路→演示 | 9 轮 · 121 步 \| LLM 21m50s · 工具调用 20m17s \| 首 token 平均 1.3s · 145 tok/s \| 缓存命中 99% \| 输入 13.9M tok · 输出 168K tok |
| 2026-09-07 工程补强轮 | 补齐缺失项 #2/#3/#4 + 单测 77 例全绿；README 更新 + 临时文件清理（无新增 LLM 耗时可记） |
