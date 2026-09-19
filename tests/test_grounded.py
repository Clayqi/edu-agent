# -*- coding: utf-8 -*-
"""grounded（引用校验 / 诚实降级）单元测试。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from edu_agent.grounded import degrade, validate
from edu_agent.generate import AnswerRecord, Citation


def _rec(answer="定义[1]", citations=None):
    return AnswerRecord(
        answer_md=answer,
        citations=citations or [],
        coverage="medium",
        confidence=0.8,
    )


class TestValidate(unittest.TestCase):
    def test_clean(self):
        rec = _rec(citations=[Citation(index=1, chapter="第三章", section="3.1", page=62)])
        self.assertEqual(validate(rec), [])

    def test_missing_citation_for_used_ref(self):
        rec = _rec("定义[1]和[2]", citations=[Citation(index=1, chapter="第三章", section="3.1")])
        issues = validate(rec)
        self.assertTrue(any("[2]" in i for i in issues))

    def test_citation_without_coordinate(self):
        rec = _rec(citations=[Citation(index=1)])
        issues = validate(rec)
        self.assertTrue(any("缺坐标" in i for i in issues))


class TestDegrade(unittest.TestCase):
    def _a(self, kind):
        return degrade("什么是x？", reason="r:" + kind, kind=kind)

    def test_empty_kind(self):
        rec = self._a("empty")
        self.assertEqual(rec.coverage, "low")
        self.assertEqual(rec.confidence, 0.0)
        self.assertIn("没有检索到", rec.answer_md)

    def test_parse_kind(self):
        rec = self._a("parse_error")
        self.assertIn("重试", rec.answer_md)

    def test_lowconf_kind(self):
        rec = self._a("low_confidence")
        self.assertIn("匹配度", rec.answer_md)

    def test_out_of_scope_kind(self):
        rec = self._a("out_of_scope")
        self.assertIn("未收录", rec.answer_md)

    def test_reason_appended(self):
        rec = degrade("Q", reason="具体原因xyz", kind="empty")
        self.assertIn("具体原因xyz", rec.answer_md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
