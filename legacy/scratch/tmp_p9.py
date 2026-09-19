# -*- coding: utf-8 -*-
import json, urllib.request, time, sys
sys.stdout.reconfigure(encoding="utf-8")
ok = False
for _ in range(75):
    try:
        c = json.loads(urllib.request.urlopen("http://127.0.0.1:7860/config", timeout=5).read().decode("utf-8"))
        ok = True; break
    except Exception:
        time.sleep(2)
print("UI ready:", ok)
if ok:
    s = json.dumps(c, ensure_ascii=False)
    print("预设含 自动路由:", "自动路由" in s)
    print("预设含 教案 Agent:", "教案 Agent" in s)
    comps = c.get("components", [])
    print("Radio 数:", sum(1 for x in comps if "radio" in str(x.get("type","")).lower()), "| Dropdown 数:", sum(1 for x in comps if "dropdown" in str(x.get("type","")).lower()))
