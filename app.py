"""Browser UI: streamlit run app.py"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from procurement_agent.erp.agent import answer as erp_answer
from procurement_agent.graph import build_graph, run_query
from procurement_agent.llm import Gemini
from procurement_agent.retrieval import ContractIndex
from procurement_agent.risks import RISK_TYPES
from procurement_agent.sample_data import ALL_CONTRACTS
from procurement_agent.tracing import Tracer

st.set_page_config(page_title="Procurement Intelligence Agent", layout="wide")


@st.cache_resource
def get_llm():
    return Gemini()


@st.cache_resource
def get_index(_llm):
    return ContractIndex(_llm, ALL_CONTRACTS)


SAMPLES = {
    "Contract review": [
        "สัญญาคอมพิวเตอร์โน้ตบุ๊กมีความเสี่ยงอะไรบ้าง ควรอนุมัติไหม",
        "สัญญา software คลังสินค้า 3 ปี มีเงื่อนไขอะไรต้องระวัง",
        "สัญญาจัดหาวัสดุสำนักงานมีเงื่อนไขอะไรที่ต้องระวัง",
    ],
    "ERP lookup": [
        "ฝ่ายไอทีมีงบประมาณเหลืออีกเท่าไหร่",
        "ใบสั่งซื้อ PO2026001 ตอนนี้อยู่ในสถานะอะไร",
        "กรีนเคมีคอลมีวงเครดิตเท่าไหร่",
    ],
}

with st.sidebar:
    st.header("Procurement Intelligence Agent")
    mode = st.radio("Mode", list(SAMPLES))
    self_check = st.checkbox("Self-check pass", value=True,
                             help="A second review pass. One more model call.")
    st.caption("Sample questions")
    for sample in SAMPLES[mode]:
        if st.button(sample, use_container_width=True, key=sample):
            st.session_state["question"] = sample

question = st.text_input("Question", key="question",
                         placeholder="ถามเรื่องสัญญา ความเสี่ยงผู้ขาย หรือข้อมูล ERP")
if not st.button("Run", type="primary") or not question.strip():
    st.stop()

llm = get_llm()
tracer = Tracer()

if mode == "Contract review":
    graph = build_graph(llm, get_index(llm), tracer, reflect=self_check)
    with st.spinner("Reviewing..."):
        result = run_query(graph, question, tracer)
    contract, vendor = result["contract"], result["vendor"]

    left, right = st.columns([2, 1])
    with left:
        st.subheader(f"{contract['id']} {contract['title']}")
        verdict = "ควรต่อรองก่อน" if result["recommendation"] == "negotiate" else "อนุมัติได้"
        st.markdown(f"**คำแนะนำ:** {verdict}")
        st.write(result["summary"])
        st.markdown("**ความเสี่ยงในสัญญา**")
        if result["review"]["risks"]:
            st.table(pd.DataFrame([
                {"ประเภท": r["type"], "ความหมาย": RISK_TYPES[r["type"]],
                 "ข้อความในสัญญา": r["clause"] or "(ไม่มีข้อกำหนด)", "เหตุผล": r["reason"]}
                for r in result["review"]["risks"]
            ]))
        else:
            st.write("ไม่พบ")
        if result["review"]["dropped"]:
            with st.expander(f"ตัดออก {len(result['review']['dropped'])} ข้อ "
                             "(อ้างข้อความที่ไม่มีในสัญญา)"):
                st.json(result["review"]["dropped"])
        with st.expander("ข้อความสัญญา"):
            st.text(contract["text"])
    with right:
        st.metric("ความเสี่ยงผู้ขาย", f"{vendor['score']}/10", vendor["level"])
        st.caption(vendor["name"])
        for reason in vendor["reasons"]:
            st.write(f"- {reason}")
else:
    with st.spinner("Asking the ERP..."), tracer.run():
        result = erp_answer(llm, question, tracer)
    for call in result["calls"]:
        st.caption(f"tool: {call['tool']}({call['args']})")
    st.write(result["answer"])

totals = tracer.totals()
st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Wall clock", f"{totals['wall_s']:.1f}s")
c2.metric("Model calls", totals["model_calls"])
c3.metric("Tokens in / out", f"{totals['tokens_in']:,} / {totals['tokens_out']:,}")
c4.metric("Est. cost", f"${totals['cost_usd']:.5f}" if totals["cost_usd"] is not None else "-")
with st.expander("Trace"):
    st.dataframe(pd.DataFrame(tracer.as_dict()["spans"]), use_container_width=True)
