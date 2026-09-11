@echo off
echo 查找并停止 5174 端口上的界面进程 ...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5174" ^| findstr "LISTENING"') do (
  taskkill /PID %%p /F >nul 2>&1
  echo 已停止 PID %%p
)
pause
