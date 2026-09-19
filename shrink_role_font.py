with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 字体缩小到10px，确保水平放下
content = content.replace('.role-seg button{flex:1;border:none;background:transparent;height:26px;border-radius:6px;font-size:11px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;writing-mode:horizontal-tb;text-orientation:mixed;overflow:visible;letter-spacing:0}',
'.role-seg button{flex:1;border:none;background:transparent;height:24px;border-radius:6px;font-size:10px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;writing-mode:horizontal-tb;text-orientation:mixed;overflow:visible;letter-spacing:0}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('教师学生字体缩小到10px')
