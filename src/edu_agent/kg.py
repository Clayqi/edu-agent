"""知识图谱模块：高中数学知识点关系图谱。

数据存储在 content/kg/ 目录下，采用轻量JSON格式，适合课程项目原型。
后续可平滑迁移到Neo4j图数据库。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
KG_DIR = ROOT / "content" / "kg"
KG_DATA = KG_DIR / "kg_data.json"


class KnowledgeGraph:
    """高中数学知识图谱（内存版）。"""

    def __init__(self) -> None:
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self.node_map: dict[str, dict] = {}
        self._loaded = False

    def load(self) -> None:
        """从JSON文件加载图谱数据。"""
        if self._loaded:
            return
        KG_DIR.mkdir(parents=True, exist_ok=True)
        if KG_DATA.exists():
            data = json.loads(KG_DATA.read_text(encoding="utf-8"))
            self.nodes = data.get("nodes", [])
            self.edges = data.get("edges", [])
            self.node_map = {n["id"]: n for n in self.nodes}
        else:
            # 如果没有数据，自动生成示例数据
            self._generate_sample()
        self._loaded = True

    def _generate_sample(self) -> None:
        """生成高中数学必修一示例知识图谱。"""
        # 节点：知识点
        self.nodes = [
            # 集合
            {"id": "set", "name": "集合", "chapter": "第一章", "type": "concept"},
            {"id": "set_def", "name": "集合的定义", "chapter": "第一章", "type": "concept"},
            {"id": "set_rel", "name": "集合间的基本关系", "chapter": "第一章", "type": "concept"},
            {"id": "set_op", "name": "集合的基本运算", "chapter": "第一章", "type": "concept"},
            {"id": "subset", "name": "子集与真子集", "chapter": "第一章", "type": "concept"},
            {"id": "equal", "name": "集合相等", "chapter": "第一章", "type": "concept"},
            {"id": "union", "name": "并集", "chapter": "第一章", "type": "concept"},
            {"id": "intersect", "name": "交集", "chapter": "第一章", "type": "concept"},
            {"id": "complement", "name": "补集", "chapter": "第一章", "type": "concept"},

            # 函数
            {"id": "function", "name": "函数", "chapter": "第三章", "type": "concept"},
            {"id": "func_def", "name": "函数的概念", "chapter": "第三章", "type": "concept"},
            {"id": "domain", "name": "定义域", "chapter": "第三章", "type": "concept"},
            {"id": "range", "name": "值域", "chapter": "第三章", "type": "concept"},
            {"id": "func_expr", "name": "函数的表示方法", "chapter": "第三章", "type": "concept"},
            {"id": "monotonic", "name": "函数的单调性", "chapter": "第三章", "type": "concept"},
            {"id": "mono_inc", "name": "增函数", "chapter": "第三章", "type": "concept"},
            {"id": "mono_dec", "name": "减函数", "chapter": "第三章", "type": "concept"},
            {"id": "extremum", "name": "函数的最大（小）值", "chapter": "第三章", "type": "concept"},
            {"id": "parity", "name": "函数的奇偶性", "chapter": "第三章", "type": "concept"},
            {"id": "even_func", "name": "偶函数", "chapter": "第三章", "type": "concept"},
            {"id": "odd_func", "name": "奇函数", "chapter": "第三章", "type": "concept"},

            # 二次函数
            {"id": "quadratic", "name": "二次函数", "chapter": "初中衔接", "type": "concept"},
            {"id": "parabola", "name": "抛物线", "chapter": "初中衔接", "type": "concept"},

            # 不等式
            {"id": "inequality", "name": "不等式", "chapter": "第二章", "type": "concept"},
            {"id": "basic_ineq", "name": "基本不等式", "chapter": "第二章", "type": "concept"},

            # 指数函数
            {"id": "exp_func", "name": "指数函数", "chapter": "第四章", "type": "concept"},
            {"id": "exp_power", "name": "n次方根与分数指数幂", "chapter": "第四章", "type": "concept"},
            {"id": "exp_prop", "name": "指数幂的运算性质", "chapter": "第四章", "type": "concept"},
        ]

        # 边：关系
        self.edges = [
            # 集合内部
            {"source": "set", "target": "set_def", "relation": "包含"},
            {"source": "set", "target": "set_rel", "relation": "包含"},
            {"source": "set", "target": "set_op", "relation": "包含"},
            {"source": "set_rel", "target": "subset", "relation": "包含"},
            {"source": "set_rel", "target": "equal", "relation": "包含"},
            {"source": "set_op", "target": "union", "relation": "包含"},
            {"source": "set_op", "target": "intersect", "relation": "包含"},
            {"source": "set_op", "target": "complement", "relation": "包含"},
            {"source": "subset", "target": "equal", "relation": "可推导"},

            # 函数内部
            {"source": "function", "target": "func_def", "relation": "包含"},
            {"source": "function", "target": "func_expr", "relation": "包含"},
            {"source": "function", "target": "monotonic", "relation": "包含"},
            {"source": "function", "target": "parity", "relation": "包含"},
            {"source": "func_def", "target": "domain", "relation": "包含"},
            {"source": "func_def", "target": "range", "relation": "包含"},
            {"source": "monotonic", "target": "mono_inc", "relation": "包含"},
            {"source": "monotonic", "target": "mono_dec", "relation": "包含"},
            {"source": "monotonic", "target": "extremum", "relation": "可推导"},
            {"source": "parity", "target": "even_func", "relation": "包含"},
            {"source": "parity", "target": "odd_func", "relation": "包含"},

            # 跨章节依赖
            {"source": "quadratic", "target": "function", "relation": "前置知识点"},
            {"source": "parabola", "target": "quadratic", "relation": "前置知识点"},
            {"source": "set", "target": "function", "relation": "前置知识点"},
            {"source": "inequality", "target": "range", "relation": "前置知识点"},
            {"source": "basic_ineq", "target": "extremum", "relation": "可推导"},
            {"source": "exp_power", "target": "exp_func", "relation": "前置知识点"},
            {"source": "exp_prop", "target": "exp_func", "relation": "前置知识点"},
            {"source": "func_def", "target": "exp_func", "relation": "前置知识点"},
        ]

        self.node_map = {n["id"]: n for n in self.nodes}
        self._save()

    def _save(self) -> None:
        """保存图谱数据到JSON文件。"""
        KG_DIR.mkdir(parents=True, exist_ok=True)
        data = {"nodes": self.nodes, "edges": self.edges}
        KG_DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_graph(self) -> dict[str, Any]:
        """返回完整图谱数据（供前端可视化）。"""
        self.load()
        # 计算每个节点的度数（连接数）
        degree = {}
        for edge in self.edges:
            degree[edge["source"]] = degree.get(edge["source"], 0) + 1
            degree[edge["target"]] = degree.get(edge["target"], 0) + 1
        
        return {
            "nodes": [
                {
                    "id": n["id"], 
                    "name": n["name"], 
                    "category": n.get("chapter", "其他"),
                    "degree": degree.get(n["id"], 0)
                } 
                for n in self.nodes
            ],
            "links": [{"source": e["source"], "target": e["target"], "relation": e["relation"]} for e in self.edges],
        }

    def get_prerequisites(self, node_id: str) -> list[dict]:
        """查询某知识点的前置知识点（向上找2层）。"""
        self.load()
        prereq = set()
        queue = [node_id]
        visited = set()

        while queue and len(prereq) < 10:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            for edge in self.edges:
                if edge["target"] == current and edge["relation"] in ("前置知识点", "可推导"):
                    prereq.add(edge["source"])
                    queue.append(edge["source"])

        result = []
        for nid in prereq:
            if nid in self.node_map:
                n = self.node_map[nid]
                result.append({"id": nid, "name": n["name"], "chapter": n.get("chapter", "")})
        return result

    def get_successors(self, node_id: str) -> list[dict]:
        """查询某知识点的后继知识点（学完这个能学什么）。"""
        self.load()
        successors = set()
        for edge in self.edges:
            if edge["source"] == node_id:
                successors.add(edge["target"])
        
        result = []
        for nid in successors:
            if nid in self.node_map:
                n = self.node_map[nid]
                result.append({"id": nid, "name": n["name"], "chapter": n.get("chapter", ""), "relation": ""})
        return result

    def get_node_info(self, node_id: str) -> dict:
        """获取节点完整信息。"""
        self.load()
        node = self.node_map.get(node_id, {})
        # 计算度数
        degree = 0
        for edge in self.edges:
            if edge["source"] == node_id or edge["target"] == node_id:
                degree += 1
        return {
            "id": node_id,
            "name": node.get("name", ""),
            "chapter": node.get("chapter", ""),
            "degree": degree,
            "prerequisites": self.get_prerequisites(node_id),
            "successors": self.get_successors(node_id)
        }

    def get_related(self, node_id: str, hops: int = 1) -> dict[str, Any]:
        """查询与某知识点相关的子图（用于高亮显示）。"""
        self.load()
        keep_nodes = {node_id}
        keep_edges = []

        for _ in range(hops):
            new_nodes = set()
            for edge in self.edges:
                if edge["source"] in keep_nodes or edge["target"] in keep_nodes:
                    keep_edges.append(edge)
                    new_nodes.add(edge["source"])
                    new_nodes.add(edge["target"])
            keep_nodes.update(new_nodes)

        nodes = [self.node_map[nid] for nid in keep_nodes if nid in self.node_map]
        return {
            "nodes": [{"id": n["id"], "name": n["name"], "category": n.get("chapter", "其他")} for n in nodes],
            "links": keep_edges,
        }

    def search_node(self, keyword: str) -> list[dict]:
        """按关键词搜索知识点节点。"""
        self.load()
        results = []
        for n in self.nodes:
            if keyword in n["name"] or keyword in n["id"]:
                results.append({"id": n["id"], "name": n["name"], "chapter": n.get("chapter", "")})
        return results[:5]


# 全局单例
_kg = KnowledgeGraph()


def get_kg() -> KnowledgeGraph:
    return _kg
