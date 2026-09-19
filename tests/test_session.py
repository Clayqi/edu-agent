# -*- coding: utf-8 -*-
"""会话管理（多轮追问）单元测试。纯数据/规则，无 IO。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from edu_agent.session import Conversation, Turn


def _conv_with(q: str = "函数的单调性怎么判断？") -> Conversation:
    c = Conversation()
    c.add("user", q)
    c.add("assistant", "单调性定义是……[1]", {"coverage": "medium", "pages": [42]})
    return c


class TestConversationBasic(unittest.TestCase):
    def test_add_and_last(self):
        c = Conversation()
        c.add("user", "问1")
        c.add("assistant", "答1")
        self.assertEqual(c.last_user_text(), "问1")
        self.assertEqual(len(c.turns), 2)

    def test_bounded(self):
        c = Conversation(max_turns=2)
        for i in range(6):
            c.add("user", f"问{i}")
            c.add("assistant", f"答{i}")
        self.assertLessEqual(len(c.turns), 4)  # 2 轮上限 -> 4 条
        self.assertNotIn("问0", [t.text for t in c.turns])

    def test_roundtrip(self):
        c = _conv_with()
        d = c.to_dict()
        c2 = Conversation.from_dict(d)
        self.assertEqual(c2.session_id, c.session_id)
        self.assertEqual(len(c2.turns), len(c.turns))
        self.assertEqual(c2.turns[0].role, "user")
        self.assertEqual(c2.turns[0].text, "函数的单调性怎么判断？")


class TestFollowUp(unittest.TestCase):
    def test_na_what(self):
        c = _conv_with()
        self.assertTrue(c.is_follow_up("那什么是增函数呢？"))

    def test_pronoun(self):
        c = _conv_with()
        self.assertTrue(c.is_follow_up("它和奇函数有什么区别？"))

    def test_short_no_topic(self):
        c = _conv_with()
        self.assertTrue(c.is_follow_up("再举个例子"))

    def test_new_full_question_is_not_followup(self):
        c = _conv_with()
        self.assertFalse(c.is_follow_up("什么是指数函数？它的图象是什么？"))

    def test_resolve_merges_previous_topic(self):
        c = _conv_with()
        rq, is_fu = c.resolve_query("那什么是增函数呢？")
        self.assertTrue(is_fu)
        self.assertIn("单调", rq)
        self.assertIn("增函数", rq)


class TestHistoryBlock(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(Conversation().history_block(), "")

    def test_content(self):
        hb = _conv_with().history_block()
        self.assertIn("上一问", hb)
        self.assertIn("单调性定义", hb)


class TestTurnMeta(unittest.TestCase):
    def test_turn_roundtrip(self):
        t = Turn.from_dict(Turn(role="assistant", text="x", meta={"pages": [1]}).to_dict())
        self.assertEqual(t.role, "assistant")
        self.assertEqual(t.meta["pages"], [1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
