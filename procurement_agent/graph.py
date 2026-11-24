"""The LangGraph workflow.

    retrieve ──┬── review_contract ──┐
               └── score_vendor ─────┴── summarize

The contract review and the vendor score run in parallel after retrieval; the
summary waits for both.
"""

from __future__ import annotations

import json
from typing import TypedDict

from procurement_agent.contract_agent import review_contract
from procurement_agent.sample_data import VENDORS
from procurement_agent.tracing import Tracer
from procurement_agent.vendor_score import score_vendor

SUMMARY_SYSTEM = """คุณเขียนสรุปให้ผู้บริหารฝ่ายจัดซื้อ ภาษาไทย ไม่ใช้ศัพท์เทคนิค
ใช้เฉพาะข้อมูลที่ให้มา ห้ามเพิ่มตัวเลขหรือเงื่อนไขที่ไม่มีในข้อมูล
recommendation:
- "negotiate" ถ้ามีความเสี่ยงในสัญญาอย่างน้อย 1 ข้อ หรือคะแนนความเสี่ยงผู้ขายตั้งแต่ 7 ขึ้นไป
- "approve" ถ้าไม่มีทั้งสองอย่าง
summary: 3-4 ประโยค บอกว่าควรอนุมัติหรือต่อรอง และต่อรองเรื่องอะไร"""

SUMMARY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "recommendation": {"type": "STRING", "enum": ["approve", "negotiate"]},
        "summary": {"type": "STRING"},
    },
    "required": ["recommendation", "summary"],
}


class State(TypedDict, total=False):
    query: str
    contract: dict
    retrieval_distance: float
    review: dict
    vendor: dict
    recommendation: str
    summary: str


def build_graph(llm, index, tracer: Tracer | None = None, reflect: bool = True,
                vendors: dict | None = None):
    from langgraph.graph import END, START, StateGraph

    vendors = VENDORS if vendors is None else vendors

    def retrieve(state: State) -> dict:
        [hit] = index.search(state["query"], k=1, tracer=tracer)
        return {"contract": hit["contract"], "retrieval_distance": hit["distance"]}

    def review(state: State) -> dict:
        return {"review": review_contract(llm, state["contract"]["text"], tracer, reflect)}

    def vendor(state: State) -> dict:
        vendor_id = state["contract"]["vendor_id"]
        history = vendors.get(vendor_id)
        node_tracer = tracer or Tracer()
        with node_tracer.timed("score_vendor"):
            result = score_vendor(history)
        name = history["name"] if history else vendor_id
        return {"vendor": {"vendor_id": vendor_id, "name": name, **result}}

    def summarize(state: State) -> dict:
        facts = {
            "question": state["query"],
            "contract": state["contract"]["title"],
            "vendor": state["vendor"],
            "contract_risks": [
                {"type": r["type"], "clause": r["clause"], "reason": r["reason"]}
                for r in state["review"]["risks"]
            ],
        }
        out = llm.generate_json("executive_summary", SUMMARY_SYSTEM,
                                json.dumps(facts, ensure_ascii=False, indent=1),
                                SUMMARY_SCHEMA, tracer)
        return {"recommendation": out["recommendation"], "summary": out["summary"]}

    graph = StateGraph(State)
    graph.add_node("retrieve", retrieve)
    graph.add_node("review_contract", review)
    graph.add_node("score_vendor", vendor)
    graph.add_node("summarize", summarize)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "review_contract")
    graph.add_edge("retrieve", "score_vendor")
    graph.add_edge(["review_contract", "score_vendor"], "summarize")
    graph.add_edge("summarize", END)
    return graph.compile()


def run_query(graph, query: str, tracer: Tracer) -> dict:
    with tracer.run():
        result = graph.invoke({"query": query})
    return {**result, "trace": tracer.as_dict()}
