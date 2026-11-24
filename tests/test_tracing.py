import time

from procurement_agent.tracing import Span, Tracer, estimate_cost


def test_cost_uses_output_price_for_thinking_tokens():
    # 1,000 in at $0.30/M and 500 out (thinking included) at $2.50/M
    assert estimate_cost(1000, 500, 0.30, 2.50) == 0.00155
    assert estimate_cost(1000, 500, None, None) is None


def test_totals_keep_wall_clock_separate_from_node_latency():
    tracer = Tracer()
    with tracer.run():
        tracer.add(Span(node="a", latency_s=1.0, model="m", tokens_in=10, tokens_out=5,
                        cost_usd=0.001))
        tracer.add(Span(node="b", latency_s=1.0, model="m", tokens_in=10, tokens_out=5,
                        cost_usd=0.002))
        with tracer.timed("code_step"):
            time.sleep(0.01)
    totals = tracer.totals()
    assert totals["model_calls"] == 2
    assert totals["cost_usd"] == 0.003
    assert totals["sum_of_node_latency_s"] >= 2.0
    assert totals["wall_s"] < 1.0  # the two spans were added, not slept
    assert "total (wall clock)" in tracer.summary()


def test_unknown_price_gives_no_total_cost():
    tracer = Tracer()
    tracer.add(Span(node="a", latency_s=0.1, model="m", cost_usd=None))
    assert tracer.totals()["cost_usd"] is None
