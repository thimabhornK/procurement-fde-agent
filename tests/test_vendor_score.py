from procurement_agent.sample_data import VENDORS
from procurement_agent.vendor_score import score_vendor


def test_reliable_vendor_scores_low():
    result = score_vendor(VENDORS["V002"])
    assert result["score"] == 1 and result["level"] == "low"


def test_late_new_vendor_with_claims_scores_high_with_reasons():
    result = score_vendor(VENDORS["V009"])
    assert result["score"] == 9 and result["level"] == "high"
    assert len(result["reasons"]) == 3


def test_inactive_vendor_and_missing_history():
    blocked = {**VENDORS["V002"], "status": "blocked"}
    assert score_vendor(blocked)["score"] == 4
    assert score_vendor(None)["score"] is None


def test_score_is_capped_at_ten():
    worst = {"orders_last_year": 2, "late_deliveries_last_year": 2,
             "quality_claims_last_year": 5, "years_as_vendor": 0, "status": "blocked"}
    assert score_vendor(worst)["score"] == 10
