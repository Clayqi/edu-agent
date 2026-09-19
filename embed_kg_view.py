"""在主页面嵌入知识星图视图"""
with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在左侧导航教材库下面加知识星图按钮
old_nav = '''        <button class="snav" data-view="library" data-ro="teacher">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V4H6.5A2.5 2.5 0 0 0 4 6.5v13z"/></svg>
          教材库
        </button>'''

new_nav = '''        <button class="snav" data-view="library" data-ro="teacher">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V4H6.5A2.5 2.5 0 0 0 4 6.5v13z"/></svg>
          教材库
        </button>
        <button class="snav" data-view="kg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M8 7l3 9M16 7l-3 9M9 6h6"/></svg>
          知识星图
        </button>'''

if 'data-view="kg"' not in content:
    content = content.replace(old_nav, new_nav)
    print('左侧导航按钮已加')

# 2. 在view-library后面加view-kg视图
old_view_end = '''        <div class="view" id="view-library">
          <div id="libBody" style="padding:20px 28px;max-width:920px"></div>
        </div>'''

new_view_end = '''        <div class="view" id="view-library">
          <div id="libBody" style="padding:20px 28px;max-width:920px"></div>
        </div>
        
        <!-- 知识星图视图 -->
        <div class="view" id="view-kg">
          <iframe src="/kg.html" style="width:100%;height:calc(100vh - 60px);border:none;border-radius:0"></iframe>
        </div>'''

if 'view-kg' not in content:
    content = content.replace(old_view_end, new_view_end)
    print('知识星图视图已加')

# 3. 把views数组里加kg
old_views = "var views = ['market','skill','chat','library','lesson','question','services'];"
new_views = "var views = ['market','skill','chat','library','kg','lesson','question','services'];"
content = content.replace(old_views, new_views)

# 4. 面包屑映射加kg
old_crumb = "var crumbText = {market:'Skill 市场',skill:'Skill 详情',chat:'新对话',library:'教材库',lesson:'我的课程',question:'我的题库',services:'MCP 服务'}[v]||'主界面';"
new_crumb = "var crumbText = {market:'Skill 市场',skill:'Skill 详情',chat:'新对话',library:'教材库',kg:'知识星图',lesson:'我的课程',question:'我的题库',services:'MCP 服务'}[v]||'主界面';"
content = content.replace(old_crumb, new_crumb)

# 5. 把教材库里的跳转按钮改成切换视图
content = content.replace("window.location.href=\\'/kg.html\\'", "switchView('kg')")
content = content.replace("window.location.href='/kg.html'", "switchView('kg')")

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('全部完成！知识星图已嵌入主页面')
