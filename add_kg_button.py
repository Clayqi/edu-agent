"""在教材库页面添加知识图谱按钮"""
with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到上传按钮的位置，在前面加知识图谱按钮
old_btn = """'<button class="pill-btn dark" id="libUp"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px;vertical-align:-2px;margin-right:5px"><path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 20h16"/></svg>上传教材 / 资料</button></div>'"""

new_btn = """'<button class="pill-btn" id="libKg" style="background:var(--blue-soft);color:var(--blue);margin-right:8px"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px;vertical-align:-2px;margin-right:5px"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M8 7l3 9M16 7l-3 9M9 6h6"/></svg>知识图谱</button>' +
        '<button class="pill-btn dark" id="libUp"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px;vertical-align:-2px;margin-right:5px"><path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 20h16"/></svg>上传教材 / 资料</button></div>'"""

if 'id="libKg"' not in content:
    content = content.replace(old_btn, new_btn)
    
    # 在libRender函数最后加事件绑定
    # 找libUp按钮的事件绑定位置
    old_event = "document.getElementById('libUp')"
    # 在它前面加libKg的事件绑定
    kg_event = """
  // 知识图谱按钮跳转
  setTimeout(function(){
    var kgBtn = document.getElementById('libKg');
    if(kgBtn) kgBtn.onclick = function(){ window.location.href = '/kg.html'; };
  }, 100);
"""
    content = content.replace(old_event, kg_event + "  document.getElementById('libUp')")
    
    with open('static/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('知识图谱按钮已添加')
else:
    print('按钮已存在')
