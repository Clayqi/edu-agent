# -*- coding: utf-8 -*-
"""generate 核心链路测试：全 mock（检索 + LLM），零网络/零 Chroma。

覆盖：plainify / classify / 解析 / 重试恢复 / 重试耗尽降级 / 检索为空降级 /
      幽灵引用清理 / 多轮追问(ask_turn) 与指代合并 / build_messages 上文块。
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import edu_agent.generate as gen
from edu_agent import session
from edu_agent.generate import AnswerRecord, build_messages, classify, plainify_math
from edu_agent.session import Conversation

OK_JSON = (
    '{"answer_md": "函数的单调性定义如下：设函数定义域为 D[1]，对任意 x1<x2，'
    '都有 f(x1)<f(x2)，则称 f 在该区间上单调递增。", '
    '"citations": [{"index": 1, "quote": "一般地，设函数 f(x) 的定义域为 I"}], '
    '"coverage": "medium", "confidence": 0.8}'
)


class FakeHit:
    def __init__(self, text="片段正文", md=None, score=0.5):
        self.text = text
        self.metadata = md or {
            "chunk_id": "c1",
            "chapter": "第三章",
            "section": "3.1",
            "heading": "函数的概念及其表示",
            "page": 62,
            "kind": "section",
        }
        self.score = score


class FakeRetrieve:
    """记录调用，返回预设命中。"""

    def __init__(self, hits=None):
        self.hits = hits if hits is not None else [FakeHit()]
        self.calls = []

    def __call__(self, query, **kw):
        self.calls.append({"query": query, "kw": kw})
        return list(self.hits)


class FakeLLMFactory:
    """每次 get_chat_llm(temperature) 返回新对象；invoke 依脚本走。"""

    def __init__(self, script):
        self.script = list(script)   # 元素: (kind, payload) kind in {"ok","raise"}
        self.calls = 0
        self.temps = []

    def __call__(self, temperature=0.0, **kw):
        self.temps.append(temperature)
        return _FakeLLM(self)

    def next_action(self):
        if self.calls < len(self.script):
            item = self.script[self.calls]
        else:
            item = ("raise", RuntimeError("script exhausted"))
        self.calls += 1
        return item


class _FakeLLM:
    def __init__(self, factory):
        self.factory = factory

    def invoke(self, messages):
        kind, payload = self.factory.next_action()
        if kind == "raise":
            raise payload
        return SimpleNamespace(content=payload)


class GenerateTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_retrieve = gen.retrieve
        self._orig_llm = gen.get_chat_llm
        self.fake_retrieve = FakeRetrieve()
        gen.retrieve = self.fake_retrieve

    def tearDown(self):
        gen.retrieve = self._orig_retrieve
        gen.get_chat_llm = self._orig_llm

    def install_llm(self, script):
        self.fake_llm = FakeLLMFactory(script)
        gen.get_chat_llm = self.fake_llm


class TestPlainify(GenerateTestBase):
    def test_dollar_and_subset(self):
        self.assertIn("⊆", plainify_math("区间 D $\\subseteq$ I"))

    def test_no_dollar_left(self):
        self.assertNotIn("$", plainify_math("$x^2$ 是平方"))

    def test_frac_braces_cleaned(self):
        out = plainify_math("\\frac{1}{2}")
        self.assertNotIn("{", out)
        self.assertNotIn("\\", out)

    def test_mathbb(self):
        self.assertIn("R", plainify_math("\\mathbb{R}"))


class TestClassifyAndParse(GenerateTestBase):
    def test_classify_delegates(self):
        self.assertEqual(classify("怎么解 4.2 例 2"), "problem")
        self.assertEqual(classify("什么是奇函数"), "concept")

    def test_parse_plain_json(self):
        rec = gen._parse_answer(OK_JSON)
        self.assertIsInstance(rec, AnswerRecord)
        self.assertEqual(len(rec.citations), 1)
        self.assertEqual(rec.citations[0].index, 1)

    def test_parse_fenced_json(self):
        fence = chr(96) * 3
        rec = gen._parse_answer(fence + "json\n" + OK_JSON + "\n" + fence)
        self.assertEqual(rec.citations[0].index, 1)

    def test_parse_invalid_raises(self):
        with self.assertRaises(ValueError):
            gen._parse_answer("not json at all")


class TestAskHappyPath(GenerateTestBase):
    def test_normal_answer(self):
        self.install_llm([("ok", OK_JSON)])
        rec = gen.ask("函数的单调性怎么判断？", retry_delay=0)
        self.assertEqual(rec.coverage, "medium")
        self.assertGreater(rec.confidence, 0.5)
        self.assertEqual(len(rec.citations), 1)
        c = rec.citations[0]
        self.assertEqual(c.page, 62)
        self.assertEqual(c.chapter, "第三章")
        self.assertIn("[1]", rec.answer_md)
        # 真实检索只被调用 1 次（无章节回退）
        self.assertEqual(len(self.fake_retrieve.calls), 1)

    def test_ghost_citation_removed(self):
        ghost = OK_JSON.replace("[1]", "[9]")
        self.install_llm([("ok", ghost)])
        rec = gen.ask("函数的单调性怎么判断？", retry_delay=0)
        # 全文只有幽灵引用 [9]：清理后 citations 空 -> 走 low_confidence 降级
        self.assertEqual(rec.coverage, "low")
        self.assertNotIn("[9]", rec.answer_md)
        # 降级记录须回显原问题（2026-09-07 修复：_regularize 曾传空串）
        self.assertIn("函数的单调性怎么判断？", rec.answer_md)

    def test_ghost_mixed_keeps_real(self):
        mixed = OK_JSON.replace("定义域为 D[1]", "定义域为 D[1]，补充[9]")
        self.install_llm([("ok", mixed)])
        rec = gen.ask("函数的单调性怎么判断？", retry_delay=0)
        self.assertEqual(len(rec.citations), 1)
        self.assertNotIn("[9]", rec.answer_md)


class TestRetry(GenerateTestBase):
    def test_recovers_after_transient_errors(self):
        self.install_llm([
            ("raise", ValueError("bad json")),
            ("raise", ValueError("bad json")),
            ("ok", OK_JSON),
        ])
        rec = gen.ask("函数的单调性怎么判断？", retry_delay=0, attempts=3)
        self.assertEqual(rec.coverage, "medium")
        self.assertEqual(self.fake_llm.calls, 3)

    def test_exhaustion_degrades_parse_error(self):
        self.install_llm([
            ("raise", ValueError("bad json 1")),
            ("raise", RuntimeError("net down")),
            ("raise", ValueError("bad json 2")),
        ])
        rec = gen.ask("函数的单调性怎么判断？", retry_delay=0, attempts=3)
        self.assertEqual(rec.coverage, "low")
        self.assertIn("重试", rec.answer_md)   # DEGRADE_PARSE 话术
        self.assertEqual(self.fake_llm.calls, 3)

    def test_single_attempt_no_retry(self):
        self.install_llm([("raise", ValueError("x"))])
        gen.ask("函数的单调性怎么判断？", retry_delay=0, attempts=1)
        self.assertEqual(self.fake_llm.calls, 1)


class TestEmptyRetrieval(GenerateTestBase):
    def test_empty_degrade(self):
        self.fake_retrieve.hits = []
        rec = gen.ask("3.2 例 2 怎么做？", retry_delay=0)
        self.assertEqual(rec.coverage, "low")
        self.assertIn("没有检索到", rec.answer_md)
        self.assertEqual(self.fake_llm.calls, 0) if hasattr(self, "fake_llm") else None


class TestMultiTurn(GenerateTestBase):
    def test_ask_turn_two_rounds(self):
        self.install_llm([("ok", OK_JSON), ("ok", OK_JSON)])
        conv = Conversation()
        rec1, conv = gen.ask_turn("函数的单调性怎么判断？", conversation=conv,
                                  retry_delay=0)
        self.assertEqual(len(conv.turns), 2)
        rec2, conv = gen.ask_turn("那什么是增函数呢？", conversation=conv,
                                  retry_delay=0)
        self.assertEqual(len(conv.turns), 4)
        # 追问被识别并记录
        self.assertTrue(conv.turns[-1].meta.get("is_follow_up"))
        # 第二次检索 query 应包含上一问话题（指代合并）
        last_call = self.fake_retrieve.calls[-1]["query"]
        self.assertIn("单调", last_call)
        self.assertIn("增函数", last_call)


class TestBuildMessages(GenerateTestBase):
    def test_history_block_present(self):
        c = Conversation()
        c.add("user", "函数的单调性怎么判断？")
        c.add("assistant", "按定义判断[1]", {"pages": [62]})
        msgs = build_messages("那什么是增函数呢？", [FakeHit()], history=c)
        user = msgs[-1]["content"]
        self.assertIn("对话上文", user)
        self.assertIn("仅作衔接理解", user)
        self.assertIn("函数的单调性怎么判断", user)

    def test_no_history_plain(self):
        msgs = build_messages("函数的单调性怎么判断？", [FakeHit()])
        user = msgs[-1]["content"]
        self.assertNotIn("对话上文", user)
        self.assertIn("学生问题", user)


class TestSessionPersistence(GenerateTestBase):
    def test_conv_dict_roundtrip_via_ask_turn(self):
        # history 形如 to_dict 也能被 ask_turn 接受
        self.install_llm([("ok", OK_JSON), ("ok", OK_JSON)])
        conv = Conversation()
        _, conv = gen.ask_turn("函数的单调性怎么判断？", conversation=conv, retry_delay=0)
        d = conv.to_dict()
        rec, conv2 = gen.ask_turn("那增函数呢", conversation=d, retry_delay=0)
        self.assertIsInstance(rec, AnswerRecord)
        self.assertEqual(len(conv2.turns), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
