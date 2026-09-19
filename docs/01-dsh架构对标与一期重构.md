# 01 · DSH 架构对标与一期重构记录

> 日期：2026-10 ｜ 范围：D:\教育agent 一期「分层 + 收口」 ｜ 验收：`tests/ 112 例全绿` + 5174 全功能
> 目标架构参照：DeepSeek Harness（DSH）—— cordis 插件组合的 host / agent / session 分层运行时。

## 0. DSH 架构一句话模型（对标基准）

- **host 平面**（base + web 组合）：进程内唯一的东西——注册表（tools/skills/subagents/goals）、
  沙箱与审批、持久化、模型路由、token 计量。代码在 `profiles/`，数据在 `sessions|storages/`。
- **agent 平面（preset）**：一个 agent = persona（身份）+ 工具面 + skills/ 目录 + 隔离域，
  声明式挂载（`agent.cordis.yml`），不拥有任何全局唯一物。
- **session 平面**：状态在插件内部按 (session, agent) 键控，可持久、可回放。
- **每个关注点一个包**：40+ `@deepseek-ai/dsh-*` 小插件，配置树 patch 按序叠加组合。
- **生命周期工程化**：plan mode / goal / 后台 job / compaction / 请求级上下文 / 技能按需加载。

## 1. 收口前的问题清单（代码级证据）

| # | 问题 | 证据 | DSH 原则对照 |
|---|---|---|---|
| P1 | 会话活在进程全局 dict + JSON 全量覆写，双 UI 双存储 | `web_server.py` SESSIONS dict + `web_sessions.json`；`api.py`(Gradio) 另存 `sessions.json` | 状态应键控持久化于 host 层 |
| P2 | 意图路由词表三处漂移 | `supervisor.PLAN_HINTS`（含"上课/导学"）≠ `graph.PLAN_HINTS`（含"课件/教案模板"），`web_server`/`api` 各抄 graph | 策略单一来源（注册表） |
| P3 | 配置散落启动脚本与模块自读 env | rerank 的 `RERANK_*` 只在 `start_*.cmd`/`retrieve.py`/`api.py`，config.py 不知情 | 配置收口一处（settings） |
| P4 | 网关承载全部业务 | web_server 路由函数内嵌 A/B/S 全套编排 | 网关薄化，业务归 agent 平面 |
| P5 | 双 UI 并存（7860 Gradio / 5174 FastAPI） | 功能重叠、会话存储分叉 | UI 合一 |
| P6 | 运行产物进仓库根 | `tmp_p*.py`、`ui_server.log`、`web_server.log`、`data/*.json` 混放 | 代码/数据分层 |
| P7 | Gradio 独有功能无主（语音/反馈/修正/日志面板） | `api.py` 560 行 | 归档留档，不回迁不丢失 |

## 2. 一期落地改动（文件级）

### 新增
- `src/edu_agent/host/__init__.py`、`host/store.py` —— **SessionStore**：SQLite(WAL,
  RLock, synchronous=NORMAL)；CRUD / 40 条消息截断 / 30 会话列表上限 / 标题 / last_html；
  旧 `web_sessions.json` 首启自动迁移并改名 `.migrated-*` 留档。  ← P1
- `src/edu_agent/routing.py` —— PLAN_HINTS/QA_HINTS/`decide(text, mode)` 单一来源。 ← P2
- `tests/test_store.py`（9 例）、`tests/test_routing.py`（6 例）。
- `docs/`（本文）。

### 改造
- `config.py`：Settings 增加 `data_dir/sessions_db/log_file/rerank_on/rerank_provider/rerank_model_dir`，
  均读 env 且可在启动时覆盖（`EDU_DATA_DIR/EDU_SESSIONS_DB/EDU_LOG_FILE/RERANK_*`）。 ← P3
- `retrieve.py`：rerank 双通道改读 settings（行为不变，env 动态生效），不再自读 os.environ。 ← P3
- `supervisor.py` / `graph.py`：词表删除，`decide/want_plan` 委托 routing；`graph.PLAN_HINTS`
  改为 routing 同一对象别名（老 import 兼容）。 ← P2
- `web_server.py`：重写为薄网关——store 替换全局 dict；auto 走 `routing.decide`；
  拆 `_stream_coach/_stream_supervisor/_stream_planner`；每个请求带 logsetup.request 上下文；
  启动预热（embedding + rerank）自 api.py 移植；`/static` 挂载保留；SSE 事件形状零改动（前端无感）。 ← P1/P2/P4/P5

### 退役/归档（不删除）
- `src/edu_agent/api.py` → `legacy/api_gradio.py`（Gradio 版：语音/反馈/修正/日志面板留档）。
- `tmp_p7/p9/v2.py` → `legacy/scratch/`；`ui_server.log`、`web_server.log` → `legacy/logs/`；
  `data/sessions.json` → `legacy/data_sessions_gradio.json`。
- `start_ui.cmd / start_web.cmd / stop_ui.cmd / run_ui.ps1 / 启动课本教练.bat` 全部收敛到 5174。
- `requirements.txt`：gradio 移出必装（注释说明需回迁时的安装方式）。

## 3. 途中修掉的实现缺陷

1. `store` 构造持锁期间迁移再取锁 → **RLock**（原 Lock 自死锁，曾致测试挂起）。
2. 消息截断切错方向：`msgs[:40]` → `msgs[-40:]`（旧版语义 = 保留最近 40 条）。
3. 测试 tearDown 需容错（Windows 文件占用）→ `TemporaryDirectory(ignore_cleanup_errors=True)`。

## 4. 验收

- `python -m unittest discover -s tests -p "test_*.py"` → **Ran 112 tests OK**（97 旧 + 15 新）。
- 5174 冒烟：首页 / 会话 CRUD / 模板 / textbook / pdfs 全部 200；SSE 事件流形状与旧版一致。
- 数据迁移冒烟：真实 `web_sessions.json` 已并入 `data/edu_sessions.db`，原文件改名留档。

## 5. 二期候选（未做，供排期）

1. **长任务模型**：B 教案 1~4 分钟阻塞 → job_id + 进度事件 + 取消（对应 DSH 后台 job）。
2. **profile 收口**：A 长期记忆/前缀的 `"default"` 硬编码 → 会话绑定 profile（DSH session 键控）。
3. **审批闸**：处分性动作（成绩定论/推送家长/强制作业）在网关加确认层（对齐铁律 6 的工程化）。
4. **headless 重放**：任意 request_id/会话可一行命令重放（logsetup 已有 request 上下文基础）。
5. **skills 目录化**：B 的模板认定/诊断协议按 SKILL.md 组织，按需加载（对齐 DSH 技能目录）。
6. **语音/反馈/修正回迁 5174**：从 `legacy/api_gradio.py` 移植（前端加控件）。
