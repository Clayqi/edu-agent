"""重新加节点详情API"""
with open('src/edu_agent/web_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找search接口的位置，在后面加node接口
old_search = '''@app.get("/api/kg/search")
def api_kg_search(q: str):
    """按关键词搜索知识点"""
    return {"results": kg.get_kg().search_node(q)}'''

new_search = '''@app.get("/api/kg/search")
def api_kg_search(q: str):
    """按关键词搜索知识点"""
    return {"results": kg.get_kg().search_node(q)}


@app.get("/api/kg/node/{node_id}")
def api_kg_node(node_id: str):
    """获取节点完整详情"""
    return kg.get_kg().get_node_info(node_id)'''

if 'api_kg_node' not in content:
    content = content.replace(old_search, new_search)
    with open('src/edu_agent/web_server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('节点详情API已添加')
else:
    print('已存在')
