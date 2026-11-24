from procurement_agent.evaluate import (
    evaluate_baseline,
    evaluate_erp,
    expected_recommendation,
    risk_scores,
)
from procurement_agent.sample_data import ALL_CONTRACTS, ERP_QUESTIONS, contract_by_id


def test_precision_recall_counts():
    scores = risk_scores([({"auto_renewal", "short_warranty"}, {"auto_renewal", "full_prepayment"}),
                          (set(), set())])
    assert (scores["tp"], scores["fp"], scores["fn"]) == (1, 1, 1)
    assert scores["precision"] == 0.5 and scores["recall"] == 0.5


def test_expected_recommendation_counts_vendor_risk():
    assert expected_recommendation(contract_by_id("C002")) == "approve"
    assert expected_recommendation(contract_by_id("C001")) == "negotiate"
    # clean contract, but the vendor scores 9
    assert expected_recommendation(contract_by_id("C009")) == "negotiate"


def test_baseline_is_reported_per_contract_set():
    report = evaluate_baseline()
    assert report["tuned"]["contracts"] == 10 and report["held_out"]["contracts"] == 6
    assert len(report["cases"]) == len(ALL_CONTRACTS)


def test_erp_check_accepts_any_name_that_resolves_to_the_same_vendor(fake_llm):
    replies = [[(c["tool"], c["args"])] for c in ERP_QUESTIONS]
    replies[0] = [("get_vendor_info", {"vendor_name": "บริษัท ABC เทคโนโลยี จำกัด"})]
    it = iter(replies)
    llm = fake_llm({"erp_choose_tool": lambda prompt: next(it)})
    assert evaluate_erp(llm, pause_s=0)["accuracy"] == 1.0
