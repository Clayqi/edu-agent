with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 把role-seg的padding去掉，让按钮撑满整个宽度
content = content.replace('.role-seg{display:flex;background:var(--bg-soft);border:.5px solid var(--line);border-radius:var(--r-pill);padding:2px;margin:0 12px 10px}',
'.role-seg{display:flex;background:var(--bg-soft);border:.5px solid var(--line);border-radius:8px;padding:2px;margin:0 12px 10px;gap:2px}')

# 字体再小一点
content = content.replace('.role-seg button{flex:1;border:none;background:transparent;height:24px;border-radius:6px;font-size:10px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;writing-mode:horizontal-tb;text-orientation:mixed;overflow:visible;letter-spacing:0}',
'.role-seg button{flex:1;border:none;background:transparent;height:22px;border-radius:6px;font-size:10px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;writing-mode:horizontal-tb;text-orientation:mixed;overflow:visible;letter-spacing:0;padding:0 4px}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('按钮宽度撑满，字体缩小，水平显示')
