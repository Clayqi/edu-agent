@echo off
rem ============================================================
rem start_web.cmd —— 启动 Agent Web UI（端口 5174，启用本地 rerank 精排）
rem 用法：双击本文件，或在终端执行 deploy\start_web.cmd
rem 停止：deploy\stop_ui.cmd（或查杀 5174 端口）
rem 便携性：用 %~dp0 定位脚本自身目录，仓库放在哪个盘/哪个目录都能跑
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0.."

rem 有本地 rerank 模型才开精排；没有则降级纯向量检索（见 start_ui.cmd 同款说明）
if exist "%~dp0..\model_cache\bge-reranker-v2-m3" (
  set RERANK_ON=1
  set RERANK_PROVIDER=local
  set RERANK_MODEL_DIR=%~dp0..\model_cache\bge-reranker-v2-m3
  echo [rerank] 找到本地精排模型，已启用
) else (
  set RERANK_ON=0
  echo [rerank] 未找到 model_cache\bge-reranker-v2-m3，按纯向量检索启动
)

echo 正在启动 Agent Web UI (127.0.0.1:5174) ...
start "" /min ".venv\Scripts\python.exe" "src\edu_agent\web_server.py"
echo.
echo 浏览器打开:  http://127.0.0.1:5174
timeout /t 5 >nul
