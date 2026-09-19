# -*- coding: utf-8 -*-
"""logsetup（日志/请求上下文）最小单测：纯 stdlib，无副作用。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from edu_agent import logsetup


class TestRequestContext(unittest.TestCase):
    def test_request_ctx_has_rid(self):
        with logsetup.request(question="q1") as ctx:
            self.assertIn("request_id", ctx)
            self.assertEqual(ctx["question"], "q1")
            self.assertTrue(len(ctx["request_id"]) >= 8)

    def test_setup_idempotent(self):
        # 重复调用不应抛错
        logsetup.setup(level="WARNING")
        logsetup.setup(level="WARNING")
        log = logsetup.get_logger("t")
        log.info("quiet")   # WARNING 级别下不应抛错/输出

    def test_event_no_crash(self):
        log = logsetup.get_logger("t")
        with logsetup.request(question="q"):
            logsetup.event(log, "probe", a=1, b="two")


if __name__ == "__main__":
    unittest.main(verbosity=2)
