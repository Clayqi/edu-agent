@echo off
chcp 65001 >nul
cd /d D:\教育agent
echo 正在启动 课本教练 x 教案 Agent Web UI（Agent S/A/B，http://127.0.0.1:5174，local rerank 已启用）...
set RERANK_ON=1
set RERANK_PROVIDER=local
set RERANK_MODEL_DIR=D:\教育agent\model_cache\bge-reranker-v2-m3
start "" /min ".venv\Scripts\python.exe" "src\edu_agent\web_server.py"
echo.
echo 浏览器打开:  http://127.0.0.1:5174
timeout /t 5 >nul
