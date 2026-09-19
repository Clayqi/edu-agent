with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在head里加防闪烁脚本
old_head = '''<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>教育 Agent · UnderstandAnything</title>
<style>'''

new_head = '''<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>教育 Agent · UnderstandAnything</title>
<script>
// 提前加载主题，防止刷新闪烁
(function(){
  const t = localStorage.getItem('theme');
  if(t === 'dark') document.documentElement.classList.add('dark');
})();
</script>
<style>'''

content = content.replace(old_head, new_head)

# 2. 优化夜间模式卡片对比度
old_dark = '''html.dark{
  --ink-900:#fafafa; --ink-700:#e4e4e7; --ink-600:#a1a1aa; --ink-500:#71717a; --ink-400:#52525b;
  --line:#27272a; --line-strong:#3f3f46;
  --bg:#18181b; --bg-soft:#1f1f23; --bg-hover:#27272a; --bg-active:#2e2e33;
  --blue:#60a5fa; --blue-soft:rgba(59,130,246,0.15);
  --green:#4ade80; --green-soft:rgba(34,197,94,0.15); --green-500:#22c55e;
  --red:#f87171; --orange:#fb923c; --amber:#fbbf24;
  --dark:#fafafa;
  --shadow-sm:0 1px 2px rgba(0,0,0,.2);
  --shadow-md:0 8px 30px rgba(0,0,0,.4);
}'''

new_dark = '''html.dark{
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

content = content.replace(old_dark, new_dark)

# 3. 底部按钮统一大小
old_btn_css = '''.sb-btn{width:34px;height:34px;border-radius:var(--r-sm);border:none;background:transparent;color:var(--ink-600);display:flex;align-items:center;justify-content:center}'''
new_btn_css = '''.sb-btn{width:32px;height:32px;border-radius:var(--r-sm);border:none;background:transparent;color:var(--ink-600);display:flex;align-items:center;justify-content:center;transition:background .2s}'''

content = content.replace(old_btn_css, new_btn_css)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('日夜模式优化完成')
