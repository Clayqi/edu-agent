with open('src/edu_agent/web_server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
added = False
for line in lines:
    new_lines.append(line)
    if 'return {"results": kg.get_kg().search_node(q)}' in line and not added:
        new_lines.append('\n\n')
        new_lines.append('@app.get("/api/kg/node/{node_id}")\n')
        new_lines.append('def api_kg_node(node_id: str):\n')
        new_lines.append('    return kg.get_kg().get_node_info(node_id)\n')
        added = True

with open('src/edu_agent/web_server.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('node接口已加' if added else '没找到位置')
