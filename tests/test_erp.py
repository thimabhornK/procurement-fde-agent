from procurement_agent.erp import tools
from procurement_agent.erp.agent import answer


def test_vendor_lookup_by_partial_name():
    result = tools.get_vendor_info("บริษัท ABC เทคโนโลยี")
    assert result["found"] and result["vendor_id"] == "V001"
    assert result["credit_limit"] == 2_000_000
    assert not tools.get_vendor_info("ไม่มีบริษัทนี้")["found"]


def test_budget_remaining():
    result = tools.check_budget("MAINTENANCE_DEPT")
    assert result["remaining"] == 300_000 and result["remaining_percent"] == 5.0
    assert not tools.check_budget("NOPE")["found"]


def test_po_status_is_case_insensitive():
    assert tools.get_po_status("po2026001")["status"] == "pending_approval"


def test_bad_arguments_return_an_error_instead_of_raising():
    assert "error" in tools.call("check_budget", {"dept": "IT_DEPT"})
    assert "error" in tools.call("delete_vendor", {})


def test_declarations_match_functions():
    assert {d["name"] for d in tools.DECLARATIONS} == set(tools.FUNCTIONS)


def test_agent_runs_the_chosen_tool_and_words_the_result(fake_llm):
    llm = fake_llm({
        "erp_choose_tool": [("check_budget", {"department": "IT_DEPT"})],
        "erp_answer": lambda prompt: "เหลือ 1,150,000 บาท" if "1150000" in prompt else "?",
    })
    result = answer(llm, "ฝ่ายไอทีเหลืองบเท่าไหร่")
    assert result["calls"][0]["result"]["remaining"] == 1_150_000
    assert result["answer"] == "เหลือ 1,150,000 บาท"


def test_agent_without_a_tool_call_does_not_ask_the_model_again(fake_llm):
    llm = fake_llm({"erp_choose_tool": []})
    result = answer(llm, "สวัสดี")
    assert result["calls"] == [] and len(llm.calls) == 1
