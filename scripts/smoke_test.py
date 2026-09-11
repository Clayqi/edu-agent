"""S1 基地验收脚本（择优后 v2）。

A. DeepSeek 连通：一问一答（期望回复「连通」）
B. embedding 连通：EMBEDDING_PROVIDER=ollama 走本地 bge-m3（期望 1024 维）
                    =siliconflow 走远程 API（需 key）

真实 Key/服务就绪后重跑本脚本直到 A/B 全绿，S1 才算完工。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from edu_agent.config import load_settings  # noqa: E402


def check_deepseek() -> bool:
    from edu_agent.config import get_chat_llm

    print("A. DeepSeek 连通：")
    try:
        llm = get_chat_llm(max_tokens=64)
        out = llm.invoke("只回复两个字：连通")
        print(f"   -> {out.content!r}")
        return True
    except RuntimeError as e:
        print(f"   [跳过待补] {e}")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"   [FAIL] DeepSeek 调用失败: {type(e).__name__}: {e}")
        print("   提示：若为 400/404 model 不存在，把 .env 的 DEEPSEEK_MODEL 改为 deepseek-chat 再试。")
        return False


def check_embedding() -> bool:
    from edu_agent.config import get_embeddings

    s = load_settings()
    print(f"B. Embedding 连通（provider={s.embedding_provider}, model={s.embedding_model}）：")
    try:
        emb = get_embeddings()
        v = emb.embed_query("函数的单调性怎么判断")
        print(f"   -> 返回维度 {len(v)}（期望 1024）")
        return len(v) == 1024
    except RuntimeError as e:
        print(f"   [跳过待补] {e}")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"   [FAIL] Embedding 调用失败: {type(e).__name__}: {e}")
        return False


def main() -> int:
    s = load_settings()
    print("===== edu-agent S1 基地验收 (v2) =====")
    print(f"LLM: {s.deepseek_model} @ {s.deepseek_base_url}   key={'就绪' if s.deepseek_ready else '占位'}")
    print(f"EMB: provider={s.embedding_provider}  model={s.embedding_model}  ollama={s.ollama_base_url}")
    print(f"路径: chroma={s.chroma_db_dir}  content={s.content_dir}  auto={s.auto_content_dir}")
    print()

    a_ok = check_deepseek()
    print()
    b_ok = check_embedding()
    print()

    skipped = (not s.deepseek_ready) and (s.embedding_provider == "siliconflow" and not s.siliconflow_ready)
    if skipped:
        print("结果：含 [跳过待补] —— Key/服务就绪后重跑本脚本补验。")
        return 0
    ok = a_ok and b_ok
    print(f"结果：{'PASS —— A/B 全绿，S1 基地验收通过 ✅' if ok else 'FAIL —— 请修 A/B 中的失败项'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
