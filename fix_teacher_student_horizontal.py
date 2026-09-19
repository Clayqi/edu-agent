with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 强化教师学生按钮文字水平
old = '''.role-seg button{flex:1;border:none;background:transparent;height:26px;border-radius:6px;font-size:11px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;writing-mode:horizontal-tb;text-orientation:mixed;overflow:visible}'''

new = '''.role-seg button{flex:1;border:none;background:transparent;height:26px;border-radius:6px;font-size:11px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;writing-mode:horizontal-tb;text-orientation:mixed;overflow:visible;letter-spacing:0}'''

content = content.replace(old, new)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('教师学生文字水平强化完成')
