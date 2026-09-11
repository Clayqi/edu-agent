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
