@echo off
chcp 65001 >nul
cd /d "D:\教育agent"
echo [1/2] 检查 Ollama (bge-m3 embedding, localhost:11434) ...
powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri http://localhost:11434/api/tags -UseBasicParsing -TimeoutSec 3).StatusCode } catch { 'DOWN' }" > "%TEMP%\ollama_check.txt"
set /p OLLAMA=<"%TEMP%\ollama_check.txt"
if "%OLLAMA%"=="DOWN" (
  echo    [警告] Ollama 未在运行！提问时 embedding 会失败。请先启动 Ollama。
  echo    (命令行执行: ollama serve  或打开 Ollama 桌面端)
) else (
  echo    [OK] Ollama 可用
)
echo [2/2] 启动 课本教练 Web UI (http://127.0.0.1:5174) ...
echo 关闭本窗口 = 停止服务。浏览器请打开 http://127.0.0.1:5174
.venv\Scripts\python.exe -u src\edu_agent\web_server.py
echo.
echo 服务已退出 (按任意键关闭)
pause >nul
