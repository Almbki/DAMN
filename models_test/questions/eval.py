"""Interactive IPIP-NEO-120 administration and scoring.

The scoring core lives in scoring.py.  Questions are resolved by stable
identity (`item_id` for the canonical bank, `id` for the legacy bank), never by
array index.

Usage:
    python eval.py                                  # canonical bank, canonical scoring
    python eval.py --mode legacy --bank questions.json   # historical reproduction
"""

from __future__ import annotations

import argparse
import json

from scoring import load_questions, score_responses

DEFAULT_BANK = "questions.json"
DEFAULT_RESULT = "result.json"


def question_key(question: dict):
    """Stable key for the answer dict; never the array index."""
    if question.get("item_id"):
        return question["item_id"]
    return question["id"]


def get_next_question_irt(remaining_questions, answered_questions, current_scores):
    """Placeholder for the future Bayesian CAT selector.

    The current full-test flow returns the next item in official order.  CAT
    will replace this function, not the scoring layer.
    """
    return remaining_questions[0]


def calculate_scores(answers, questions, mode: str = "canonical"):
    """Backward-compatible wrapper around scoring.score_responses."""
    return score_responses(answers, questions, mode=mode)


def main() -> None:
    parser = argparse.ArgumentParser(description="IPIP-NEO-120 full test")
    parser.add_argument("--bank", default=DEFAULT_BANK, help="question bank JSON")
    parser.add_argument(
        "--mode",
        choices=("canonical", "legacy"),
        default="canonical",
        help="canonical = official ItemKey metadata; legacy = pre-migration audit only",
    )
    parser.add_argument("--result", default=DEFAULT_RESULT, help="output result JSON")
    args = parser.parse_args()

    bank = args.bank

    print("=" * 50)
    print(" 大五人格测试 (IPIP-NEO-120) - 全量测试模式")
    print(" 1=非常不准确, 2=比较不准确, 3=一般, 4=比较准确, 5=非常准确")
    print(f" bank={bank} mode={args.mode}")
    print("=" * 50)

    try:
        questions = load_questions(bank)
    except Exception as exc:
        print(f"加载失败: {exc}")
        return

    answers = {}
    remaining_questions = questions.copy()
    total_questions = len(questions)

    while remaining_questions:
        next_q = get_next_question_irt(remaining_questions, answers, None)
        q_id = question_key(next_q)
        q_text = next_q["text"]
        progress = len(answers) + 1

        while True:
            try:
                ans = int(input(f"[{progress}/{total_questions}] {q_text} (1-5): "))
                if 1 <= ans <= 5:
                    answers[q_id] = ans
                    break
                print("  [!] 请输入 1 到 5 之间的数字。")
            except ValueError:
                print("  [!] 请输入有效的数字。")

        remaining_questions.remove(next_q)

    result_data = calculate_scores(answers, questions, mode=args.mode)

    with open(args.result, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=4)

    print("\n" + "=" * 50)
    print(f"✅ 测试完成！结果已保存至: {args.result}")
    print("=" * 50)


if __name__ == "__main__":
    main()
