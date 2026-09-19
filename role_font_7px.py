with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('.role-seg button{flex:1;border:none;background:transparent;height:20px;border-radius:6px;font-size:9px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;overflow:visible;letter-spacing:0;padding:0 2px}',
'.role-seg button{flex:1;border:none;background:transparent;height:20px;border-radius:6px;font-size:7px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;overflow:visible;letter-spacing:0;padding:0 2px}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('字体改为7px')
