# 贡献指南（edu-agent）

> 完整的团队协作与版本迭代说明见 `docs/03-团队协作与版本迭代.md`；本文件是**每个提交前必须过一遍的清单**。

## 一、分支怎么用

| 分支 | 用途 |
|---|---|
| `main` | 主干，随时可跑；只通过 PR 合并 |
| `feat/<模块>-<内容>` | 新功能，例 `feat/rag-rerank` |
| `fix/<模块>-<内容>` | 修 bug，例 `fix/panel-label` |
| `hotfix/<内容>` | 演示/交付现场急修，从 `main` 直接拉 |

禁止直接向 `main` 推提交（建议仓库开启 branch protection 强制 PR）。

## 二、按目录认领，别踩别人的模块

| 模块 | 目录/文件 |
|---|---|
| 教材 / RAG | `src/edu_agent/{ingest,pdf_import,pdf_upload,retrieve,bm25_index,ollama_embeddings,figdetect,page_image}.py`、`scripts/`、`content/` |
| Agent 生成 | `src/edu_agent/{generate,prompts,graph,planner,supervisor,routing,session,memory,template_spec,plan_html,math_verify,mcp_tools}.py` |
| 网关 / 前端 | `src/edu_agent/web_server.py`、`src/edu_agent/host/store.py`、`static/`、`start_*.cmd` |
| 测试 / 文档 | `tests/`、`docs/`、`README.md`、`CHANGELOG.md` |
| 教材库（**单人负责**） | `chroma_db/`、`content/structured_auto/`（二进制/自动生成，多人同改必冲突） |

热点共享文件（改动前先 `git pull --rebase origin main`）：`README.md`、`static/index.html`、`web_server.py`、`prompts.py`。

## 二之二、路径写法（硬规则：跨机器必须能跑）

仓库里**禁止出现盘符绝对路径**（如 `D:\教育agent\...`、`C:/xxx`）—— 每个组员的 clone 位置都不同，写死一处就废掉一个功能（2026-09-11 修过一批：启动脚本、清洗脚本、Web 默认目录）。

| 场景 | 正确写法 |
|---|---|
| Windows 启动脚本 `.cmd` | `cd /d "%~dp0.."`（`%~dp0` = 脚本自身所在目录，`..` 回仓库根） |
| PowerShell `.ps1` | `$root = Split-Path -Parent $PSScriptRoot` |
| Python 脚本 | `Path(__file__).resolve().parents[N]` 再拼相对路径 |
| 可配置目录（数据/模型/工作区） | 环境变量 + `config.py` 的 `load_settings()`（如 `EDU_DATA_DIR`、`EDU_FS_ROOT`） |
| 前端默认目录 | 从后端接口拿（如不带 `path` 调 `GET /api/fs/list`），不要在前端写死 |

PR 前自查（应无输出）：

```bash
grep -rn "[A-Z]:[\\/]" --include='*.py' --include='*.cmd' --include='*.ps1' --include='*.html' src scripts deploy static
```


## 三、提交前清单

```bash
# 1) 先跑测试（必须全绿：Ran 112 tests, OK）
.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"

# 2) 改了这些要重启服务（5174）：prompts.py / generate.py / web_server.py / host/store.py
#    只改 static/ 不用重启，刷新浏览器即可

# 3) 别把本地产物提交进去（.gitignore 已挡，检查一下）
git status --short          # 不应出现 .env / data/ / model_cache/ / *.bak-*

# 4) ⚠️ chroma_db/chroma.sqlite3 会「假脏」：只要读过向量库（跑了一次问答/脚本/单测），
#    sqlite 就会重写该文件 —— 内容其实没变（片段数与元数据一致），git 却显示 M。
#    处理：不是真要更新教材库就丢弃它：git checkout -- chroma_db/chroma.sqlite3
#    （实测：git checkout 后再读一次，文件 md5 又变回同一个值 → 证明是读写噪声，不是数据变更）
```

## 四、提交消息

格式：`type(模块): 做了什么，为什么`

- `feat(rag): 加入 rerank 双通道，长句检索命中率提升`
- `fix(ui): 修侧栏圆钮标签被下一行遮挡`
- `docs(readme): 补 2026-09-10 更新章节`
- `test(store): 补 append(meta=) 用例`

## 五、提 PR

推分支后打开：
`https://github.com/Clayqi/edu-agent/compare/main...<你的分支名>?expand=1`

PR 里写清：**改了什么 / 怎么验的 / 有没有动别人的模块**。合并用 Squash and merge。

## 六、国内网络

- 有 Clash：`git config http.proxy http://127.0.0.1:7897`（关掉后记得 unset）
- 无 Clash：让有代理的同学给整包
  `https://ghfast.top/https://github.com/Clayqi/edu-agent/archive/refs/heads/main.tar.gz`
  或用 Gitee「导入 GitHub 仓库」做只读镜像，clone 国内快。
