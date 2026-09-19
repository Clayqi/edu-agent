# -*- coding: utf-8 -*-
"""WPS MCP 适配层测试（capabilities / mcp_tools 多服务 / wps_export）。

设计：**默认全离线**，不启动 WPS、不联网、不起 MCP 子进程。
- 开关闸门、路径解析、白名单、PPT 本地生成 都能在本机无 WPS 的情况下验；
- 真调 WPS 的用例统一 `skipUnless(EDU_TEST_WPS=1)`，换台机器不会因此报红。

用法：
    python -m unittest discover -s tests -p "test_*.py"
    EDU_TEST_WPS=1 python -m unittest tests.test_wps_tools     # 额外跑真·WPS 导出
"""
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

_PROJ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJ / "src"))

from edu_agent import capabilities as cap          # noqa: E402
from edu_agent import mcp_tools, wps_export        # noqa: E402

# web_server 在 import 时会建 SessionStore，先把数据根指到临时目录，避免污染本机
os.environ.setdefault("EDU_DATA_DIR", tempfile.mkdtemp(prefix="edu_test_data_"))  # noqa: E402
from edu_agent import web_server as ws             # noqa: E402

WPS_LIVE = os.getenv("EDU_TEST_WPS") == "1" and cap.wps_entry().exists()


class _EnvSandbox(unittest.TestCase):
    """把 EDU_DATA_DIR / WPS_MCP_* 指向临时目录，避免污染本机真实状态。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old = {k: os.environ.get(k) for k in
                     ("EDU_DATA_DIR", "WPS_MCP_DIR", "WPS_MCP_ENTRY")}
        os.environ["EDU_DATA_DIR"] = self._tmp.name
        os.environ.pop("WPS_MCP_DIR", None)
        os.environ.pop("WPS_MCP_ENTRY", None)
        cap._CACHE.clear()
        self.addCleanup(self._restore)

    def _restore(self):
        for k, v in self._old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        cap._CACHE.clear()
        self._tmp.cleanup()


class TestGate(_EnvSandbox):
    """开关闸门：关掉就不该起子进程、不该导出。"""

    def test_default_on(self):
        self.assertTrue(cap.is_enabled("mcp", "wps-office"))
        self.assertTrue(cap.is_enabled("skill", "wps-word"))
        self.assertTrue(cap.is_enabled("skill", "doc-session-preview"), "会话预览默认开启")


class TestSessionDocPreview(_EnvSandbox):
    """会话内文档预览：纯内存、不落盘、不碰 WPS，且与落盘导出解耦。

    对应「会话内内存预览」与「WPS 落盘导出」两条链路的分离：
    关掉 wps-office 导出被拒，但预览照常；关掉 doc-session-preview 预览不渲染，但导出照常。
    """

    MD = """# 3.3 幂函数

**教学目标**
- 理解幂函数的概念。

**教学过程**
### 情境导入（约 5 分钟）
投影实例。
### 课堂小结（约 3 分钟）
回顾路径。
"""

    def test_capability_registered_and_builtin(self):
        row = [s for s in cap.snapshot()["skills"] if s["id"] == "doc-session-preview"]
        self.assertEqual(len(row), 1)
        self.assertTrue(row[0]["builtin"], "内置能力（没有 skills/<id>/SKILL.md）")
        self.assertTrue(row[0]["enabled"])
        self.assertTrue(row[0]["active"], "不依赖 MCP，开启即生效")

    def test_status_field(self):
        self.assertTrue(cap.snapshot()["session_doc_preview_ready"])
        cap.set_enabled("skill", "doc-session-preview", False)
        self.assertFalse(cap.snapshot()["session_doc_preview_ready"])
        self.assertFalse(cap.session_preview_ready())

    def test_preview_is_pure_no_disk_no_wps(self):
        """预览只做内存整理：不落盘、不调用 WPS 客户端。"""
        before = set(p.name for p in wps_export.resolve_out_dir(None).glob("*")) \
            if wps_export.resolve_out_dir(None).exists() else set()
        called = []
        orig = wps_export.mcp_tools.call_sequence
        wps_export.mcp_tools.call_sequence = lambda *a, **k: called.append(a) or []
        os.environ["WPS_MCP_ENTRY"] = str(Path(self._tmp.name) / "nope" / "index.js")
        cap._CACHE.clear()
        try:
            r = ws.api_session_doc_preview(ws.DocPreviewReq(markdown=self.MD))
        finally:
            wps_export.mcp_tools.call_sequence = orig
        self.assertTrue(r["ok"], r.get("error"))
        self.assertEqual(called, [], "预览不得触发任何 MCP 调用")
        after = set(p.name for p in wps_export.resolve_out_dir(None).glob("*")) \
            if wps_export.resolve_out_dir(None).exists() else set()
        self.assertEqual(before, after, "预览不得往导出目录写文件")

    def test_preview_echoes_input(self):
        r = ws.api_session_doc_preview(ws.DocPreviewReq(markdown=self.MD,
                                                        payload={"title": "自定义标题"}))
        self.assertEqual(r["markdown"], self.MD, "markdown 原样回传")
        self.assertEqual(r["payload"], {"title": "自定义标题"}, "payload 原样回传")
        self.assertEqual(r["title"], "自定义标题", "payload 标题优先")
        self.assertEqual([s["name"] for s in r["slides"]], ["情境导入", "课堂小结"])
        self.assertEqual(r["stats"]["minutes"], 8)
        self.assertGreater(r["stats"]["blocks"], 0)

    def test_preview_still_works_when_wps_off(self):
        """★ 两条链路解耦：关掉 WPS 导出被拒，预览照常。"""
        cap.set_enabled("mcp", "wps-office", False)
        self.assertFalse(cap.wps_available()[0])
        exp = wps_export.export({"title": "x", "steps": [{"name": "导入"}]}, kind="docx")
        self.assertFalse(exp["ok"])
        self.assertEqual(exp.get("gate"), "capability")
        prev = ws.api_session_doc_preview(ws.DocPreviewReq(markdown=self.MD))
        self.assertTrue(prev["ok"], "预览不该被 WPS 开关影响")

    def test_export_still_works_when_preview_off(self):
        """★ 反向解耦：关掉会话预览，导出链路一行不受影响。"""
        cap.set_enabled("skill", "doc-session-preview", False)
        self.assertFalse(cap.session_preview_ready())
        prev = ws.api_session_doc_preview(ws.DocPreviewReq(markdown=self.MD))
        self.assertTrue(prev["ok"], "接口仍可用")
        self.assertFalse(prev["enabled"], "但会告诉前端：别渲染面板")
        self.assertTrue(cap.is_enabled("mcp", "wps-office"), "WPS 开关未被连带关闭")

    def test_status_endpoint_exposes_field(self):
        st = ws.api_mcp_status()
        self.assertIn("session_doc_preview_ready", st)
        cap.set_enabled("skill", "doc-session-preview", False)
        self.assertFalse(ws.api_mcp_status()["session_doc_preview_ready"])

    def test_toggle_persists(self):
        self.assertTrue(cap.set_enabled("mcp", "wps-office", False)["ok"])
        self.assertFalse(cap.is_enabled("mcp", "wps-office"))
        self.assertTrue((Path(self._tmp.name) / "capabilities.json").exists())
        cap.set_enabled("mcp", "wps-office", True)
        self.assertTrue(cap.is_enabled("mcp", "wps-office"))

    def test_unknown_capability_rejected(self):
        self.assertFalse(cap.set_enabled("mcp", "no-such-service", True)["ok"])

    def test_disabled_short_circuits_client(self):
        """关掉后 list_tools 直接返回 []（不 gate 通过 → 不起 node 子进程）。"""
        cap.set_enabled("mcp", "wps-office", False)
        self.assertEqual(mcp_tools.list_tools("wps-office"), [])
        self.assertIsNone(mcp_tools.call_tool("wps-office", "wps_common_ping", {}))

    def test_disabled_blocks_export(self):
        cap.set_enabled("mcp", "wps-office", False)
        self.assertFalse(cap.wps_available()[0])
        r = wps_export.export({"title": "闸门测试", "steps": []}, kind="docx")
        self.assertFalse(r["ok"])
        self.assertEqual(r["gate"], "capability")

    def test_skill_follows_its_mcp(self):
        """关掉 MCP，绑定它的 Skill 应显示为未生效。"""
        cap.set_enabled("mcp", "wps-office", False)
        rows = {s["id"]: s for s in cap.snapshot()["skills"]}
        self.assertTrue(rows["wps-word"]["enabled"])       # Skill 自身没关
        self.assertFalse(rows["wps-word"]["active"])       # 但依赖关了就未生效

    def test_math_whitelist_still_blocked(self):
        """白名单外一律 None（且不触碰 IO）。"""
        self.assertIsNone(mcp_tools.mcp_call("rm_rf_evil", expr="x"))
        self.assertIn("derivative", mcp_tools.ALLOWED)
        self.assertIsNone(mcp_tools.call_tool("no-such-server", "whatever", {}))


class TestPathResolution(_EnvSandbox):
    """第三方装在仓库外：路径解析优先级 + 未安装时的表现。"""

    def test_entry_outside_repo(self):
        repo = _PROJ.resolve()
        entry = cap.wps_entry()
        self.assertNotIn(str(repo), str(entry), "WPS MCP 入口不应落在仓库内")

    def test_env_entry_wins(self):
        fake = Path(self._tmp.name) / "deps" / "wps-office-mcp" / "dist" / "index.js"
        os.environ["WPS_MCP_ENTRY"] = str(fake)
        cap._CACHE.clear()
        self.assertEqual(cap.wps_entry(), fake)

    def test_missing_install_is_reported_not_crashed(self):
        os.environ["WPS_MCP_ENTRY"] = str(Path(self._tmp.name) / "nope" / "index.js")
        cap._CACHE.clear()
        ok, why = cap.wps_available()
        self.assertFalse(ok)
        row = [m for m in cap.snapshot()["mcp"] if m["id"] == "wps-office"][0]
        self.assertFalse(row["running"])
        self.assertFalse(row["entry_exists"])
        self.assertIn("setup_wps_mcp", row["detail"])
        # 未安装时调用应安全短路，而不是抛异常
        self.assertEqual(mcp_tools.list_tools("wps-office"), [])
        self.assertIsNone(mcp_tools.call_tool("wps-office", "wps_common_ping", {}))

    def test_skills_dir_follows_wps_root(self):
        os.environ["WPS_MCP_DIR"] = str(Path(self._tmp.name) / "wps-skills")
        cap._CACHE.clear()
        self.assertEqual(cap.wps_skills_dir(),
                         Path(self._tmp.name) / "wps-skills" / "skills")


class TestOutDirAndNaming(_EnvSandbox):
    def test_default_out_dir(self):
        self.assertEqual(wps_export.resolve_out_dir(None), wps_export.OUT_DIR)
        self.assertEqual(wps_export.resolve_out_dir(""), wps_export.OUT_DIR)

    def test_custom_out_dir_created(self):
        target = Path(self._tmp.name) / "我的导出" / "深层"
        self.assertEqual(wps_export.resolve_out_dir(str(target)), target)
        self.assertTrue(target.is_dir())

    def test_safe_name_strips_illegal(self):
        self.assertEqual(wps_export._safe_name("3.3 幂函数"), "3.3_幂函数")
        self.assertNotIn("/", wps_export._safe_name("a/b:c*d?e"))
        self.assertTrue(wps_export._safe_name(""))


class TestPptxLocal(_EnvSandbox):
    """PPT 走 python-pptx 本地生成：无 WPS 也能验产物。"""

    PAYLOAD = {"title": "3.3 幂函数", "grade": "重点班 45 分钟",
               "steps": [{"name": "情境导入", "minutes": 5, "bullets": ["回顾指数函数", "提出问题"]},
                         {"name": "概念建构", "minutes": 15, "bullets": ["五个常见幂函数"]},
                         {"name": "练习巩固", "minutes": 25, "bullets": ["比较大小"]}]}

    def test_native_pptx(self):
        out = Path(self._tmp.name) / "deck.pptx"
        info = wps_export.pptx_native("3.3 幂函数", "重点班", self.PAYLOAD["steps"], out)
        self.assertTrue(out.exists())
        self.assertEqual(out.read_bytes()[:2], b"PK")          # 真 OOXML
        self.assertEqual(info["slides"], 4)                     # 封面 + 3 环节
        with zipfile.ZipFile(out) as z:
            slides = [n for n in z.namelist() if n.startswith("ppt/slides/slide")]
        self.assertEqual(len(slides), 4)

    def test_export_pptx_shape_without_wps(self):
        """未安装/被关闭时，ppt 导出不会崩，返回明确的失败原因。"""
        os.environ["WPS_MCP_ENTRY"] = str(Path(self._tmp.name) / "nope" / "index.js")
        cap._CACHE.clear()
        r = wps_export.export(self.PAYLOAD, kind="pptx",
                              out_dir=str(Path(self._tmp.name) / "out"))
        self.assertFalse(r["ok"])
        self.assertIn(r.get("gate"), ("capability", "mcp", "local"))


class TestSlidesFromMarkdown(unittest.TestCase):
    """教案 Markdown -> PPT 页（预览与实际生成共用，所以这里锁住形状）。

    背景：原先 pptx_native 的 markdown 分支只认 `## ` 标题，而 Agent B 的教案用的是
    `**板块**` + `### 环节` —— 于是「对话里导出 PPT」会出来一份几乎空白的 PPT。
    """

    PLAN = """# 3.3 幂函数

**教学目标**
- 理解幂函数的概念，能识别 y=x^α 的形式。[1]
- 掌握五个常见幂函数的图象与性质。

**教学过程**

### 情境导入（约 5 分钟）
投影课本 p89 五个实例，学生写解析式并找共同特征。[2]
### 概念建构（约 12 分钟）
给出定义，强调底数为自变量、指数为常数。
- 追问：y=2x^2 是不是幂函数
| 误导 | 表格不进 PPT |

### 课堂小结（约 3 分钟）
回顾研究路径。

**板书设计**
左侧定义，右侧图象对照表。
"""

    def test_h3_preferred(self):
        d = wps_export.slides_from_markdown(self.PLAN)
        self.assertEqual(d["title"], "3.3 幂函数")
        self.assertEqual(d["source"], "h3", "有 ### 环节时以环节分页")
        self.assertEqual([s["name"] for s in d["slides"]], ["情境导入", "概念建构", "课堂小结"])

    def test_minutes_split_out_of_title(self):
        d = wps_export.slides_from_markdown(self.PLAN)
        self.assertEqual(d["slides"][0]["minutes"], "5")
        self.assertNotIn("分钟", d["slides"][0]["name"], "时长进 minutes，标题里不再重复")

    def test_citations_stripped_and_table_skipped(self):
        d = wps_export.slides_from_markdown(self.PLAN)
        s0 = d["slides"][0]["bullets"][0]
        self.assertNotIn("[2]", s0, "幻灯片上不该出现引用角标")
        joined = " ".join(b for s in d["slides"] for b in s["bullets"])
        self.assertNotIn("表格不进 PPT", joined, "表格内容留给 Word")

    def test_paragraph_line_becomes_bullet(self):
        d = wps_export.slides_from_markdown(self.PLAN)
        b = d["slides"][1]["bullets"]
        self.assertIn("给出定义，强调底数为自变量、指数为常数。", b)
        self.assertIn("追问：y=2x^2 是不是幂函数", b)

    def test_falls_back_to_sections(self):
        md = "# 单调性\n\n**教学目标**\n- 理解定义。\n**教学过程**\n- 讲三步。\n"
        d = wps_export.slides_from_markdown(md)
        self.assertEqual(d["source"], "section")
        self.assertEqual([s["name"] for s in d["slides"]], ["教学目标", "教学过程"])

    def test_falls_back_to_h2(self):
        md = "# 课题\n\n## 第一段\n- 要点\n"
        d = wps_export.slides_from_markdown(md)
        self.assertEqual(d["source"], "h2")
        self.assertEqual([s["name"] for s in d["slides"]], ["第一段"])

    def test_empty_markdown_is_safe(self):
        d = wps_export.slides_from_markdown("")
        self.assertEqual(d["slides"], [])
        self.assertEqual(d["title"], "")


@unittest.skipUnless(WPS_LIVE, "需要本机 WPS + 已安装 wps-skills（设 EDU_TEST_WPS=1 开启）")
class TestWpsLive(_EnvSandbox):
    """真·WPS 端到端（默认 skip，避免没有 WPS 的机器报红）。"""

    def test_bridge_ping(self):
        out = mcp_tools.call_tool("wps-office", "wps_common_ping", {}, timeout=60)
        self.assertIsNotNone(out)
        self.assertIn("success", str(out))

    def test_export_docx(self):
        r = wps_export.export({"title": "自检教案", "grade": "40 分钟",
                               "steps": [{"name": "导入", "minutes": 5, "bullets": ["要点一"]}]},
                              kind="docx", out_dir=self._tmp.name)
        self.assertTrue(r["ok"], r.get("error"))
        self.assertEqual(Path(r["path"]).read_bytes()[:2], b"PK")


if __name__ == "__main__":
    unittest.main()
