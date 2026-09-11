@echo off
rem ============================================================
rem start_ui.cmd —— 启动课本教练 Web UI（端口 5174，启用本地 rerank 精排）
rem 便携性：%~dp0 = 本脚本目录(deploy\)，%~dp0.. = 仓库根 → 放哪个盘都能跑
rem 停止：deploy\stop_ui.cmd ｜ 顶层等价入口：启动课本教练.bat
rem ============================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
set "PY=%~dp0..\.venv\Scripts\python.exe"

rem --- 虚拟环境自检：缺 .venv 时给出可照做的修复命令，而不是一闪而过 ---
if not exist "%PY%" (
  echo [错误] 未找到虚拟环境: %PY%
  echo 修复：在仓库根目录执行
  echo     python -m venv .venv
  echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

rem --- rerank：本地模型存在才开精排；缺失自动降级为纯向量检索（新人 clone 后没有 model_cache）---
if exist "%~dp0..\model_cache\bge-reranker-v2-m3" (
  set RERANK_ON=1
  set RERANK_PROVIDER=local
  set RERANK_MODEL_DIR=%~dp0..\model_cache\bge-reranker-v2-m3
  echo [rerank] 找到本地精排模型，已启用
) else (
  set RERANK_ON=0
  echo [rerank] 未找到 model_cache\bge-reranker-v2-m3，按纯向量检索启动（不影响答疑）
)

echo 正在启动 课本教练 x 教案 Agent Web UI（Agent S/A/B，http://127.0.0.1:5174）...
start "" /min "%PY%" -u "src\edu_agent\web_server.py"
echo.
echo 浏览器打开:  http://127.0.0.1:5174
timeout /t 5 >nul
