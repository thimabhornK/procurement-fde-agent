"""Evaluation against the labelled synthetic contracts.

    python -m procurement_agent.evaluate                  # model run, writes reports/eval.json
    python -m procurement_agent.evaluate --self-check both  # with and without the self-check pass
    python -m procurement_agent.evaluate --baseline-only  # keyword baseline, no API key needed

What is measured:
- retrieval: the right contract ranked first, over two phrasings per contract
- risk detection: precision and recall of risk types against the labels, for
  the model and for a keyword baseline, reported separately for the ten
  contracts the prompts and keyword rules were written against and for six
  held-out contracts in different wording
- grounding: how many quoted clauses were not in the contract and were dropped
- recommendation: approve / negotiate against the expected decision
- ERP tool choice: right tool and arguments chosen by function calling
- latency (wall clock per question), model calls, tokens and cost
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from procurement_agent.erp import tools as erp_tools
from procurement_agent.risks import RISK_TYPES, baseline_risks
from procurement_agent.sample_data import ALL_CONTRACTS, ERP_QUESTIONS, VENDORS
from procurement_agent.tracing import Tracer
from procurement_agent.vendor_score import score_vendor

REPORTS = Path("reports")


def expected_recommendation(contract: dict) -> str:
    score = score_vendor(VENDORS.get(contract["vendor_id"]))["score"] or 0
    return "negotiate" if contract["risks"] or score >= 7 else "approve"


def risk_scores(pairs: list[tuple[set, set]]) -> dict:
    """Micro precision / recall / F1 over (predicted, expected) type sets."""
    per_type = {t: {"tp": 0, "fp": 0, "fn": 0} for t in RISK_TYPES}
    for predicted, expected in pairs:
        for t in predicted & expected:
            per_type[t]["tp"] += 1
        for t in predicted - expected:
            per_type[t]["fp"] += 1
        for t in expected - predicted:
            per_type[t]["fn"] += 1
    tp = sum(v["tp"] for v in per_type.values())
    fp = sum(v["fp"] for v in per_type.values())
    fn = sum(v["fn"] for v in per_type.values())
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
            "tp": tp, "fp": fp, "fn": fn, "per_type": per_type}


def by_set(pairs: list[tuple[str, set, set]]) -> dict:
    """Risk scores per contract set: 'tuned' (C001-C010) and 'held_out' (H001-H006)."""
    out = {}
    for name in ("tuned", "held_out"):
        subset = [(p, e) for s, p, e in pairs if s == name]
        if subset:
            out[name] = {"contracts": len(subset), **risk_scores(subset)}
    return out


def evaluate_baseline() -> dict:
    pairs, rows = [], []
    for c in ALL_CONTRACTS:
        predicted = set(baseline_risks(c["text"]))
        pairs.append((c["set"], predicted, set(c["risks"])))
        rows.append({"contract": c["id"], "set": c["set"], "expected": sorted(c["risks"]),
                     "predicted": sorted(predicted)})
    return {**by_set(pairs), "cases": rows}


def evaluate_retrieval(index) -> dict:
    rows, hits = [], 0
    for c in ALL_CONTRACTS:
        for q in c["queries"]:
            [hit] = index.search(q, k=1)
            ok = hit["contract"]["id"] == c["id"]
            hits += ok
            rows.append({"query": q, "expected": c["id"], "got": hit["contract"]["id"],
                         "distance": hit["distance"], "ok": ok})
    return {"questions": len(rows), "hit_at_1": round(hits / len(rows), 3),
            "misses": [r for r in rows if not r["ok"]]}


def evaluate_pipeline(llm, index, reflect: bool, pause_s: float, limit: int | None) -> dict:
    from procurement_agent.graph import build_graph, run_query

    pairs, rows, latencies, traces = [], [], [], []
    dropped_total = quoted_total = rec_ok = 0
    for c in ALL_CONTRACTS[:limit]:
        tracer = Tracer()
        graph = build_graph(llm, index, tracer, reflect=reflect)
        query = c["queries"][0]
        try:
            result = run_query(graph, query, tracer)
        except Exception as exc:  # keep going; the failure is part of the result
            rows.append({"contract": c["id"], "query": query, "error": str(exc)[:300]})
            continue
        got = result["contract"]
        predicted = {r["type"] for r in result["review"]["risks"]}
        expected = set(got["risks"])
        pairs.append((got["set"], predicted, expected))
        dropped = result["review"]["dropped"]
        dropped_total += len(dropped)
        quoted_total += len(result["review"]["risks"]) + len(dropped)
        want = expected_recommendation(got)
        rec_ok += result["recommendation"] == want
        latencies.append(tracer.wall_s)
        traces.append(tracer.totals())
        rows.append({
            "contract": c["id"], "query": query, "retrieved": got["id"],
            "expected_risks": sorted(expected), "predicted_risks": sorted(predicted),
            "first_pass_risks": result["review"]["first_pass_types"],
            "dropped_by_grounding": dropped,
            "recommendation": result["recommendation"], "expected_recommendation": want,
            "summary": result["summary"], "trace": tracer.as_dict(),
        })
        time.sleep(pause_s)

    done = len(latencies)
    if not done:
        return {"questions": 0, "errors": rows}
    costs = [t["cost_usd"] for t in traces if t["cost_usd"] is not None]
    ordered = sorted(latencies)
    return {
        "self_check": reflect,
        "questions": done,
        "errors": sum("error" in r for r in rows),
        "risk_detection": by_set(pairs),
        "grounding": {"risks_quoted": quoted_total, "dropped_not_in_contract": dropped_total},
        "recommendation_accuracy": round(rec_ok / done, 3),
        "latency_s": {"median": round(statistics.median(ordered), 2),
                      "p95": round(ordered[min(done - 1, int(0.95 * done))], 2),
                      "max": round(ordered[-1], 2)},
        "model_calls_per_question": round(statistics.mean(t["model_calls"] for t in traces), 2),
        "tokens_per_question": {
            "in": round(statistics.mean(t["tokens_in"] for t in traces)),
            "out": round(statistics.mean(t["tokens_out"] for t in traces)),
            "thinking": round(statistics.mean(t["thinking_tokens"] for t in traces)),
        },
        "cost_per_question_usd": round(statistics.mean(costs), 6) if costs else None,
        "cases": rows,
    }


def _same_target(name: str, got: dict, want: dict) -> bool:
    if name == "get_vendor_info":
        a = erp_tools.get_vendor_info(got.get("vendor_name", ""))
        b = erp_tools.get_vendor_info(want["vendor_name"])
        return a.get("found", False) and a.get("vendor_id") == b.get("vendor_id")
    if name == "get_po_status":
        return got.get("po_number", "").strip().upper() == want["po_number"]
    return got == want


def evaluate_erp(llm, pause_s: float) -> dict:
    rows, correct = [], 0
    for case in ERP_QUESTIONS:
        calls = llm.choose_tools("erp_choose_tool", "เรียก tool ที่ตอบคำถามได้",
                                 case["question"], erp_tools.DECLARATIONS)
        name, args = calls[0] if calls else (None, {})
        ok = name == case["tool"] and _same_target(name, args, case["args"])
        correct += ok
        rows.append({"question": case["question"], "expected": case["tool"],
                     "expected_args": case["args"], "got": name, "got_args": args, "ok": ok})
        time.sleep(pause_s)
    return {"questions": len(rows), "accuracy": round(correct / len(rows), 3),
            "misses": [r for r in rows if not r["ok"]]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-check", choices=["on", "off", "both"], default="on")
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="evaluate the first N contracts")
    parser.add_argument("--pause", type=float, default=0.0,
                        help="seconds between questions, for rate-limited keys")
    args = parser.parse_args()

    report = {"baseline_keywords": evaluate_baseline()}
    if args.baseline_only:
        _write(report, "eval_baseline.json")
        return

    from procurement_agent.llm import Gemini
    from procurement_agent.retrieval import ContractIndex

    llm = Gemini()
    report["model"] = llm.model
    report["embedding_model"] = llm.settings.embedding_model
    report["thinking_budget"] = llm.settings.thinking_budget
    report["date"] = time.strftime("%Y-%m-%d")
    index = ContractIndex(llm, ALL_CONTRACTS)
    report["retrieval"] = evaluate_retrieval(index)
    modes = {"on": [True], "off": [False], "both": [True, False]}[args.self_check]
    report["pipeline"] = [evaluate_pipeline(llm, index, m, args.pause, args.limit)
                          for m in modes]
    report["erp_tool_choice"] = evaluate_erp(llm, args.pause)
    _write(report, "eval.json")


def _write(report: dict, name: str) -> None:
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / name
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(_headline(report))
    print(f"\nFull report: {path}")


def _headline(report: dict) -> str:
    def pr(scores: dict) -> str:
        return "  ".join(f"{name}: P {v['precision']:.0%} R {v['recall']:.0%}"
                         for name, v in scores.items())

    lines = [f"Keyword baseline        {pr(_sets(report['baseline_keywords']))}"]
    if "retrieval" in report:
        lines.append(f"Retrieval hit@1         {report['retrieval']['hit_at_1']:.0%} "
                     f"of {report['retrieval']['questions']}")
    for p in report.get("pipeline", []):
        if not p.get("questions"):
            lines.append("Pipeline                no question completed")
            continue
        tag = "with self-check" if p["self_check"] else "no self-check  "
        cost = p["cost_per_question_usd"]
        lines.append(
            f"Model {tag}   {pr(p['risk_detection'])}\n"
            f"                        recommendation {p['recommendation_accuracy']:.0%}  "
            f"median {p['latency_s']['median']}s  p95 {p['latency_s']['p95']}s  "
            f"{p['model_calls_per_question']} calls"
            + (f"  ${cost:.5f}/question" if cost is not None else "")
        )
    if "erp_tool_choice" in report:
        lines.append(f"ERP tool choice         {report['erp_tool_choice']['accuracy']:.0%} "
                     f"of {report['erp_tool_choice']['questions']}")
    return "\n".join(lines)


def _sets(scores: dict) -> dict:
    return {k: v for k, v in scores.items() if k in ("tuned", "held_out")}


if __name__ == "__main__":
    main()
