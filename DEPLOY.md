# edu-agent 团队本地部署指南

> 课本教练 × 教案 Agent：以教材为唯一事实来源的高中数学多 Agent 项目。
> 本文档面向**团队本地部署与二次开发**。开发主文档见 README.md（架构/模块/测试）。

## 0. 仓库包含什么

```
src/edu_agent/        全部后端（Agent A/B/S + 检索 + host 层 + web 网关）
static/               前端（单文件 index.html + vendor）
tests/                112 例单测（全 mock，零网络）
content/structured_auto/   教材自动切节文本（5 章 52 节，向量化源）
chroma_db/            预建向量库（151 块，clone 后即可检索）
requirements.txt      依赖清单
.env.example          环境配置样例（复制为 .env）
```

**不入库**（部署者自行准备，见 §3）：`.env`（密钥）、`data/`（运行时）、
`model_cache/`（rerank 模型 2.2GB，可选）、教材源 PDF（版权文件，预建向量库已含知识）。

## 1. 环境要求

- Python 3.11+（建议 3.11）
- 本机 Ollama（跑 embedding 模型 bge-m3）：`ollama pull bge-m3`，默认 `http://localhost:11434`
- DeepSeek API Key（https://platform.deepseek.com 申请）

## 2. 一键本地部署

```bash
# 1) 克隆
git clone git@github.com:Clayqi/edu-agent.git   # 或 https 方式
cd edu-agent

# 2) 装依赖（建议虚拟环境）
python -m venv .venv
.venv/Scripts/activate            # Windows
# source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt

# 3) 配置环境
cp .env.example .env              # 填入 DEEPSEEK_API_KEY

# 4) 确认 Ollama bge-m3 就绪（冒烟）
curl http://localhost:11434/api/version   # 应返回版本 JSON

# 5) 启动 Web（端口 5174）
.venv/Scripts/python.exe -u src/edu_agent/web_server.py
# 或 Windows:  start_web.cmd
```

浏览器打开 http://127.0.0.1:5174/ —— 可直接对话（预建向量库已含教材知识）。

## 3. 可选：重建教材知识库 / 加新教材

clone 自带 chroma_db（151 块）。若想重新切节入库（或换教材 PDF）：

1. 自备教材 PDF（人教A版），编辑 `.env`：`TEXTBOOK_PDF=D:\path\to\教材.pdf`
2. 重新切节：`python -m edu_agent.pdf_import`（生成 content/structured_auto/*.md）
3. 重新入库：`python -m edu_agent.ingest`（幂等全量重建 chroma_db）

> 注意：教材文本/向量库为内部资料，私有仓库内使用；勿公开分发教材 PDF。

## 4. 修改与开发

- **测试**（改完必跑，112 例全 mock 零网络零 LLM）：
  ```bash
  .venv/Scripts/python.exe -m unittest discover -s tests
  ```
- **模块结构**见 README.md「结构」节；架构分层/一期收口见 docs/01-dsh架构对标与一期重构.md
- 前端为单文件 `static/index.html`（自包含），后端不改也可独立改 UI
- 运行时数据落在 `data/`（会话 SQLite/上传 PDF/日志），删掉即重置，不影响代码
- 默认关 rerank（内存省）；要开：`RERANK_ON=1` + model_cache 模型

## 5. 常见问题

| 现象 | 处理 |
|---|---|
| 页面能开但发消息没反应 | 看浏览器 Console（F12）红色报错；确认服务进程活着 |
| 回复"检索无结果/未收录" | 确认 .env 的 TEXTBOOK_PDF 未误配；chroma_db 存在 |
| 首次提问很慢 | Ollama bge-m3 首次加载需几秒，之后常驻 |
| 想重置全部会话 | 停服务后删除 data/edu_sessions.db 再启动 |
