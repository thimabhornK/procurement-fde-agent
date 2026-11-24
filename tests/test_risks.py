from procurement_agent.risks import RISK_TYPES, baseline_risks, ground
from procurement_agent.sample_data import contract_by_id


def test_grounding_drops_a_clause_that_is_not_in_the_contract():
    text = contract_by_id("C001")["text"]
    risks = [
        {"type": "full_prepayment", "clause": "ผู้ซื้อชำระเงิน 100% ล่วงหน้าก่อนส่งมอบ", "reason": "r"},
        {"type": "liability_cap_low", "clause": "ผู้ขายรับผิดไม่เกิน 1 บาท", "reason": "made up"},
    ]
    kept, dropped = ground(risks, text)
    assert [r["type"] for r in kept] == ["full_prepayment"]
    assert dropped[0]["dropped_because"] == "clause_not_in_contract"


def test_grounding_ignores_whitespace_differences_and_duplicate_types():
    text = contract_by_id("C001")["text"]
    risks = [
        {"type": "auto_renewal", "clause": "สัญญาต่ออายุอัตโนมัติทุกปี  เว้นแต่", "reason": "r"},
        {"type": "auto_renewal", "clause": "สัญญาต่ออายุอัตโนมัติทุกปี", "reason": "again"},
    ]
    kept, dropped = ground(risks, text)
    assert len(kept) == 1 and not dropped


def test_absence_risk_needs_no_quote_but_other_types_do():
    kept, dropped = ground(
        [{"type": "weak_late_penalty", "clause": "", "reason": "no penalty"},
         {"type": "auto_renewal", "clause": "", "reason": "no quote"},
         {"type": "not_a_type", "clause": "x", "reason": ""}],
        "any text",
    )
    assert [r["type"] for r in kept] == ["weak_late_penalty"]
    assert {d["dropped_because"] for d in dropped} == {"no_clause_quoted", "unknown_type"}


def test_keyword_baseline_on_a_tuned_contract():
    assert set(baseline_risks(contract_by_id("C001")["text"])) == {
        "full_prepayment", "auto_renewal", "weak_late_penalty"}


def test_labels_use_known_types_only():
    from procurement_agent.sample_data import ALL_CONTRACTS
    for contract in ALL_CONTRACTS:
        assert set(contract["risks"]) <= set(RISK_TYPES), contract["id"]
