with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 删掉设置弹窗里的主题切换部分
old = '''    <div style="margin-bottom:16px">
      <div style="font-size:13px;color:var(--ink-500);margin-bottom:10px">外观主题</div>
      <div style="display:flex;flex-direction:column;gap:8px">
        <button onclick="setTheme('light')" id="themeLight" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg-soft);cursor:pointer;text-align:left">
          <span>☀️</span><span style="font-size:13px">日间模式</span>
        </button>
        <button onclick="setTheme('dark')" id="themeDark" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg-soft);cursor:pointer;text-align:left">
          <span>🌙</span><span style="font-size:13px">夜间模式</span>
        </button>
      </div>
    </div>'''

new = '''    <div style="font-size:13px;color:var(--ink-500)">主题切换请使用左下角的太阳/月亮按钮</div>'''

content = content.replace(old, new)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('设置弹窗里的主题切换已删除')
