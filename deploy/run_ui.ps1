$ErrorActionPreference = "Continue"
$py = "D:\教育agent\.venv\Scripts\python.exe"
Write-Output ("PYTHON " + $py)
& $py -u "D:\教育agent\src\edu_agent\web_server.py"
Write-Output ("PYEXIT " + $LASTEXITCODE)
