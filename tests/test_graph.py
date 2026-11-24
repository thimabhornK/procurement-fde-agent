import json

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("chromadb")

from procurement_agent.graph import build_graph, run_query  # noqa: E402
from procurement_agent.retrieval import ContractIndex  # noqa: E402
from procurement_agent.sample_data import ALL_CONTRACTS  # noqa: E402
from procurement_agent.tracing import Tracer  # noqa: E402

PREPAY = {"type": "full_prepayment", "clause": "ผู้ซื้อชำระเงิน 100% ล่วงหน้าก่อนส่งมอบ",
          "reason": "จ่ายก่อนรับของ"}


def summary(prompt):
    facts = json.loads(prompt)
    risky = facts["contract_risks"] or (facts["vendor"]["score"] or 0) >= 7
    return {"recommendation": "negotiate" if risky else "approve",
            "summary": f"{facts['contract']}: ผู้ขายคะแนน {facts['vendor']['score']}"}


def make(fake_llm, risks):
    return fake_llm({
        "contract_first_pass": {"risks": risks},
        "contract_self_check": {"risks": risks},
        "executive_summary": summary,
    })


def test_retrieval_finds_the_contract_by_its_own_wording(fake_llm):
    index = ContractIndex(make(fake_llm, []), ALL_CONTRACTS)
    [hit] = index.search("สัญญาซื้อขายคอมพิวเตอร์โน้ตบุ๊ก จำนวน 15 เครื่อง")
    assert hit["contract"]["id"] == "C001"


def test_full_run_reviews_scores_and_summarizes(fake_llm):
    llm = make(fake_llm, [PREPAY])
    index = ContractIndex(llm, ALL_CONTRACTS)
    tracer = Tracer()
    graph = build_graph(llm, index, tracer)
    result = run_query(graph, "สัญญาซื้อขายคอมพิวเตอร์โน้ตบุ๊ก 15 เครื่อง", tracer)

    assert result["contract"]["id"] == "C001"
    assert result["vendor"]["score"] == 8
    assert [r["type"] for r in result["review"]["risks"]] == ["full_prepayment"]
    assert result["recommendation"] == "negotiate"
    nodes = [s["node"] for s in result["trace"]["spans"]]
    assert {"contract_first_pass", "contract_self_check", "score_vendor",
            "executive_summary"} <= set(nodes)
    assert nodes[-1] == "executive_summary"  # the summary waited for both branches
    assert result["trace"]["totals"]["model_calls"] == 3


def test_summary_sees_only_grounded_risks(fake_llm):
    invented = {"type": "liability_cap_low", "clause": "ไม่มีข้อนี้ในสัญญา", "reason": "x"}
    llm = make(fake_llm, [invented])
    graph = build_graph(llm, ContractIndex(llm, ALL_CONTRACTS), Tracer())
    result = graph.invoke({"query": "สัญญาจัดหาวัสดุสำนักงาน ระยะเวลา 1 ปี"})
    assert result["contract"]["id"] == "C002"
    assert result["review"]["risks"] == []
    summary_prompt = [p for n, p in llm.calls if n == "executive_summary"][0]
    assert "liability_cap_low" not in summary_prompt
    assert result["recommendation"] == "approve"
