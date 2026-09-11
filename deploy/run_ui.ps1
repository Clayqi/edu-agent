# run_ui.ps1 —— 前台运行 Web UI（便于直接看日志/退出码）
# 便携性：$PSScriptRoot = 本脚本目录(deploy\)，其父目录 = 仓库根 → 放哪个盘都能跑
# 顶层等价入口：启动课本教练.bat ｜ 后台启动：deploy\start_web.cmd
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Output ("[错误] 未找到虚拟环境: " + $py)
    Write-Output "请在仓库根目录执行: python -m venv .venv ; .venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

Write-Output ("PYTHON " + $py)
& $py -u (Join-Path $root "src\edu_agent\web_server.py")
Write-Output ("PYEXIT " + $LASTEXITCODE)
