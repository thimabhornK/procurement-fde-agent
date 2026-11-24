from procurement_agent.contract_agent import review_contract
from procurement_agent.sample_data import contract_by_id
from procurement_agent.tracing import Tracer

TEXT = contract_by_id("C001")["text"]
PREPAY = {"type": "full_prepayment", "clause": "ผู้ซื้อชำระเงิน 100% ล่วงหน้าก่อนส่งมอบ", "reason": "r"}
RENEW = {"type": "auto_renewal", "clause": "สัญญาต่ออายุอัตโนมัติทุกปี", "reason": "r"}
INVENTED = {"type": "liability_cap_low", "clause": "ผู้ขายรับผิดไม่เกิน 1 บาท", "reason": "r"}


def test_self_check_result_is_used_and_grounded(fake_llm):
    llm = fake_llm({
        "contract_first_pass": {"risks": [PREPAY, INVENTED]},
        "contract_self_check": {"risks": [PREPAY, RENEW, INVENTED]},
    })
    tracer = Tracer()
    result = review_contract(llm, TEXT, tracer)
    assert [r["type"] for r in result["risks"]] == ["full_prepayment", "auto_renewal"]
    assert result["dropped"][0]["type"] == "liability_cap_low"
    assert result["first_pass_types"] == ["full_prepayment", "liability_cap_low"]
    assert [s.node for s in tracer.spans] == ["contract_first_pass", "contract_self_check"]


def test_self_check_prompt_contains_the_contract(fake_llm):
    llm = fake_llm({"contract_first_pass": {"risks": []},
                    "contract_self_check": {"risks": []}})
    review_contract(llm, TEXT)
    node, prompt = llm.calls[1]
    assert node == "contract_self_check" and "100% ล่วงหน้า" in prompt


def test_skipping_the_self_check_makes_one_call(fake_llm):
    llm = fake_llm({"contract_first_pass": {"risks": [RENEW]}})
    result = review_contract(llm, TEXT, reflect=False)
    assert len(llm.calls) == 1
    assert [r["type"] for r in result["risks"]] == ["auto_renewal"]
