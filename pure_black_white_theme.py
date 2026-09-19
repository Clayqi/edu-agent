with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 调整日间模式：白底黑字
old_light = ''':root{
  --ink-900:#1a1a1b; --ink-700:#3f3f46; --ink-600:#52525b; --ink-500:#71717a; --ink-400:#a1a1aa;
  --line:#ececec; --line-strong:#d9d9d9;
  --bg:#ffffff; --bg-soft:#fafafa; --bg-hover:#f4f4f4; --bg-active:#f1f1f0;
  --blue:#3b82f6; --blue-soft:#eff6ff;
  --green:#16a34a; --green-soft:#dcfce7; --green-500:#22c55e;
  --red:#dc2626; --orange:#f97316; --amber:#b45309;
  --dark:#1a1a1b;
  --r-xs:6px; --r-sm:8px; --r-md:10px; --r-lg:14px; --r-xl:18px; --r-pill:999px;
  --shadow-sm:0 1px 2px rgba(0,0,0,.04);
  --shadow-md:0 8px 30px rgba(0,0,0,.10);
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI","Inter","Helvetica Neue","Microsoft YaHei",system-ui,sans-serif;
}'''

new_light = ''':root{
  --ink-900:#000000; --ink-700:#222222; --ink-600:#444444; --ink-500:#666666; --ink-400:#999999;
  --line:#e5e5e5; --line-strong:#cccccc;
  --bg:#ffffff; --bg-soft:#f8f8f8; --bg-hover:#f0f0f0; --bg-active:#eeeeee;
  --blue:#000000; --blue-soft:#eeeeee;
  --green:#16a34a; --green-soft:#dcfce7; --green-500:#22c55e;
  --red:#dc2626; --orange:#f97316; --amber:#b45309;
  --dark:#000000;
  --r-xs:6px; --r-sm:8px; --r-md:10px; --r-lg:14px; --r-xl:18px; --r-pill:999px;
  --shadow-sm:0 1px 2px rgba(0,0,0,.1);
  --shadow-md:0 8px 30px rgba(0,0,0,.15);
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI","Inter","Helvetica Neue","Microsoft YaHei",system-ui,sans-serif;
}'''

content = content.replace(old_light, new_light)

# 调整夜间模式：黑底白字
old_dark = '''html.dark{
  --ink-900:#f5f5f5; --ink-700:#e5e5e5; --ink-600:#b0b0b0; --ink-500:#888888; --ink-400:#666666;
  --line:#2a2a2a; --line-strong:#3a3a3a;
  --bg:#1a1a1a; --bg-soft:#242424; --bg-hover:#2e2e2e; --bg-active:#333333;
  --blue:#60a5fa; --blue-soft:rgba(59,130,246,0.2);
  --green:#4ade80; --green-soft:rgba(34,197,94,0.2); --green-500:#22c55e;
  --red:#f87171; --orange:#fb923c; --amber:#fbbf24;
  --dark:#fafafa;
  --shadow-sm:0 1px 2px rgba(0,0,0,.3);
  --shadow-md:0 8px 30px rgba(0,0,0,.5);
}'''

new_dark = '''html.dark{
  --ink-900:#ffffff; --ink-700:#eeeeee; --ink-600:#bbbbbb; --ink-500:#999999; --ink-400:#666666;
  --line:#333333; --line-strong:#444444;
  --bg:#000000; --bg-soft:#171717; --bg-hover:#222222; --bg-active:#2a2a2a;
  --blue:#ffffff; --blue-soft:#2a2a2a;
  --green:#4ade80; --green-soft:rgba(34,197,94,0.2); --green-500:#22c55e;
  --red:#f87171; --orange:#fb923c; --amber:#fbbf24;
  --dark:#ffffff;
  --shadow-sm:0 1px 2px rgba(0,0,0,.5);
  --shadow-md:0 8px 30px rgba(0,0,0,.7);
}'''

content = content.replace(old_dark, new_dark)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('主题调整：日间白底黑字，夜间黑底白字')
