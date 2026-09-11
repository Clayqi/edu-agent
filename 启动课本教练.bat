@echo off
rem ============================================================
rem 启动课本教练.bat —— 顶层唯一入口：环境自检 → 启动 Web UI（5174）
rem 便携性：用 %~dp0 定位仓库根，仓库放在哪个盘/目录都能跑
rem 等价入口：deploy\start_ui.cmd（带 rerank）、deploy\run_ui.ps1（前台看日志）
rem ============================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"

rem --- 1/3 虚拟环境自检（新人 clone 后最容易漏的一步）---
if not exist "%PY%" (
  echo [错误] 未找到虚拟环境: %PY%
  echo 修复：在本目录执行
  echo     python -m venv .venv
  echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

rem --- 2/3 Ollama（bge-m3 embedding，检索/问答的前置依赖）---
echo [1/2] 检查 Ollama (bge-m3 embedding, localhost:11434) ...
powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri http://localhost:11434/api/tags -UseBasicParsing -TimeoutSec 3).StatusCode } catch { 'DOWN' }" > "%TEMP%\ollama_check.txt"
set /p OLLAMA=<"%TEMP%\ollama_check.txt"
if "%OLLAMA%"=="DOWN" (
  echo    [警告] Ollama 未在运行！提问时 embedding 会失败。请先启动 Ollama。
  echo    (命令行执行: ollama serve  或打开 Ollama 桌面端)
) else (
  echo    [OK] Ollama 可用
)

rem --- 3/3 启动 Web UI ---
echo [2/2] 启动 课本教练 Web UI (http://127.0.0.1:5174) ...
echo 关闭本窗口 = 停止服务。浏览器请打开 http://127.0.0.1:5174
"%PY%" -u "src\edu_agent\web_server.py"
echo.
echo 服务已退出 (按任意键关闭)
pause >nul
