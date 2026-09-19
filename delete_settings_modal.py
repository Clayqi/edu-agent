with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 删掉设置弹窗
old_modal = '''<!-- 设置弹窗 -->
<div id="settingsModal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:1000;align-items:center;justify-content:center" onclick="if(event.target===this)this.style.display='none'">
  <div style="background:var(--bg);border-radius:12px;padding:24px;width:320px;box-shadow:0 20px 60px rgba(0,0,0,0.3)">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
      <h3 style="font-size:16px;font-weight:600">设置</h3>
      <button onclick="document.getElementById('settingsModal').style.display='none'" style="border:none;background:none;font-size:20px;cursor:pointer;color:var(--ink-500)">×</button>
    </div>
    <div style="font-size:13px;color:var(--ink-500)">主题切换请使用左下角的太阳/月亮按钮</div>
  </div>
</div>'''

content = content.replace(old_modal, '')

# 把齿轮按钮的点击事件改成什么都不做，或者改成切换主题
content = content.replace('onclick="document.getElementById(\'settingsModal\').style.display=\'flex\'"', '')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('设置弹窗已删除')
