# run_ui.ps1 —— 前台运行 Web UI（便于直接看日志/调试退出码）
# 便携性：用 $PSScriptRoot 定位脚本所在目录（deploy\），上一级即仓库根，
#        所以仓库放在哪个盘/哪个目录都能跑，不写死盘符。
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
Write-Output ("PYTHON " + $py)
& $py -u (Join-Path $root "src\edu_agent\web_server.py")
Write-Output ("PYEXIT " + $LASTEXITCODE)
