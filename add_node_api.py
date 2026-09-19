"""加节点详情API接口"""
with open('src/edu_agent/web_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

node_api = '''

@app.get("/api/kg/node/{node_id}")
def api_kg_node(node_id: str):
    """获取节点完整详情"""
    return kg.get_kg().get_node_info(node_id)
'''

if '/api/kg/node/' not in content:
    # 在search接口后面加
    content = content.replace(
        '@app.get("/api/kg/search")\ndef api_kg_search(q: str):\n    """按关键词搜索知识点"""\n    return {"results": kg.get_kg().search_node(q)}',
        '@app.get("/api/kg/search")\ndef api_kg_search(q: str):\n    """按关键词搜索知识点"""\n    return {"results": kg.get_kg().search_node(q)}' + node_api
    )
    with open('src/edu_agent/web_server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('节点详情API已添加')
else:
    print('API已存在')
