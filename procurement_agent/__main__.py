"""python -m procurement_agent "สัญญาคอมพิวเตอร์โน้ตบุ๊กมีความเสี่ยงอะไรบ้าง" [--trace]"""

from __future__ import annotations

import argparse

from procurement_agent.graph import build_graph, run_query
from procurement_agent.llm import Gemini
from procurement_agent.retrieval import ContractIndex
from procurement_agent.risks import RISK_TYPES
from procurement_agent.sample_data import ALL_CONTRACTS
from procurement_agent.tracing import Tracer


def main() -> None:
    parser = argparse.ArgumentParser(description="Review a contract and get a recommendation.")
    parser.add_argument("question")
    parser.add_argument("--no-self-check", action="store_true",
                        help="skip the second review pass (one model call fewer)")
    parser.add_argument("--trace", action="store_true", help="print latency, tokens and cost")
    args = parser.parse_args()

    llm = Gemini()
    index = ContractIndex(llm, ALL_CONTRACTS)
    tracer = Tracer()
    graph = build_graph(llm, index, tracer, reflect=not args.no_self_check)
    result = run_query(graph, args.question, tracer)

    contract, vendor = result["contract"], result["vendor"]
    print(f"สัญญา: {contract['id']} {contract['title']}")
    print(f"ผู้ขาย: {vendor['name']}  ความเสี่ยงผู้ขาย {vendor['score']}/10 ({vendor['level']})")
    print("\nความเสี่ยงในสัญญา:")
    for risk in result["review"]["risks"] or []:
        clause = f'  "{risk["clause"]}"' if risk["clause"] else ""
        print(f"- {risk['type']}: {RISK_TYPES[risk['type']]}\n  {risk['reason']}{clause}")
    if not result["review"]["risks"]:
        print("- ไม่พบ")
    print(f"\nคำแนะนำ: {result['recommendation']}\n{result['summary']}")
    if args.trace:
        print("\n" + tracer.summary())


if __name__ == "__main__":
    main()
