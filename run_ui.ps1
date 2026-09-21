$ErrorActionPreference = "Continue"
$py = "D:\edu-agent\.venv\Scripts\python.exe"
Write-Output ("PYTHON " + $py)
& $py -u "D:\edu-agent\src\edu_agent\web_server.py"
Write-Output ("PYEXIT " + $LASTEXITCODE)