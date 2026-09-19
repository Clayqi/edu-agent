with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 字体缩小到9px，按钮高度20px，确保两个字水平放下
content = content.replace('.role-seg button{flex:1;border:none;background:transparent;height:22px;border-radius:6px;font-size:10px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;writing-mode:horizontal-tb;text-orientation:mixed;overflow:visible;letter-spacing:0;padding:0 4px}',
'.role-seg button{flex:1;border:none;background:transparent;height:20px;border-radius:6px;font-size:9px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;overflow:visible;letter-spacing:0;padding:0 2px}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('字体9px，按钮20px，肯定水平放下了')
