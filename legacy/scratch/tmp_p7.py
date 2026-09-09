# -*- coding: utf-8 -*-
import urllib.request, time, sys, subprocess
sys.stdout.reconfigure(encoding="utf-8")
ok = False
for _ in range(60):
    try:
        h = urllib.request.urlopen("http://127.0.0.1:7860", timeout=5).read().decode("utf-8","ignore")
        ok = True; break
    except Exception:
        time.sleep(2)
print("UI ready:", ok)
if ok:
    print("深色主题css:", "#0f1115" in h)
out = subprocess.run(["netstat","-ano"], capture_output=True, text=True).stdout
lst = [l.split() for l in out.splitlines() if ":7860" in l and "LISTENING" in l]
print("监听PID:", lst[0][-1] if lst else "无")
