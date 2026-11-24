"""python -m procurement_agent.erp "ฝ่ายไอทีมีงบเหลือเท่าไหร่" [--trace]"""

from __future__ import annotations

import argparse

from procurement_agent.erp.agent import answer
from procurement_agent.llm import Gemini
from procurement_agent.tracing import Tracer


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the ERP agent a question.")
    parser.add_argument("question")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()

    tracer = Tracer()
    with tracer.run():
        result = answer(Gemini(), args.question, tracer)
    for call in result["calls"]:
        print(f"[tool] {call['tool']}({call['args']})")
    print(result["answer"])
    if args.trace:
        print("\n" + tracer.summary())


if __name__ == "__main__":
    main()
