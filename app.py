"""
Streamlit frontend สำหรับ Procurement Intelligence Agent
รันด้วยคำสั่ง: streamlit run app.py
"""

import streamlit as st
from google import genai

import config
from agents import document_agent
from data.sample_data import CONTRACTS
from orchestrator_langgraph import build_graph
from mcp.erp_agent import run_erp_query
from utils.tracing import Tracer

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Procurement Intelligence Agent",
    page_icon="📋",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  /* Base */
  [data-testid="stAppViewContainer"] { background: #0f1117; }
  [data-testid="stSidebar"] { background: #161b27; border-right: 1px solid #1e2533; }

  /* Typography */
  h1 { font-size: 1.6rem !important; font-weight: 700 !important; letter-spacing: -0.5px; }
  h2 { font-size: 1.1rem !important; font-weight: 600 !important; color: #94a3b8 !important; }
  p, li { color: #cbd5e1; font-size: 0.92rem; line-height: 1.65; }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: #161b27;
    border: 1px solid #1e2533;
    border-radius: 10px;
    padding: 16px 20px;
  }
  [data-testid="stMetricValue"] { font-size: 1.4rem !important; color: #e2e8f0 !important; }
  [data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.78rem !important; }

  /* Trace row */
  .trace-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 16px; margin: 4px 0;
    background: #161b27; border-radius: 8px;
    border-left: 3px solid #3b82f6;
  }
  .trace-node { color: #93c5fd; font-weight: 600; font-size: 0.85rem; }
  .trace-stat { color: #64748b; font-size: 0.8rem; }

  /* Summary box */
  .summary-box {
    background: linear-gradient(135deg, #0f2744 0%, #0f1f3d 100%);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 24px 28px;
    margin-top: 8px;
  }
  .summary-box p { color: #bfdbfe; line-height: 1.8; }

  /* Tag */
  .tag {
    display: inline-block; padding: 2px 10px;
    border-radius: 20px; font-size: 0.72rem; font-weight: 600;
    background: #1e3a5f; color: #60a5fa; margin-right: 6px;
  }
  .tag-green { background: #14532d; color: #4ade80; }
  .tag-yellow { background: #422006; color: #fb923c; }
</style>
""", unsafe_allow_html=True)

# ── Google Cloud client (cached) ──────────────────────────────────────────────

@st.cache_resource
def get_client():
    return genai.Client(vertexai=True, project=config.PROJECT_ID, location=config.LOCATION)

@st.cache_resource
def get_collection(_client):
    return document_agent.build_index(_client, CONTRACTS, config)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 📋 Procurement Agent")
    st.caption("Powered by Gemini 2.5 Flash · Vertex AI")
    st.divider()

    mode = st.radio(
        "Mode",
        ["Contract Analysis", "ERP Query"],
        help="Contract Analysis: วิเคราะห์สัญญาและความเสี่ยงผู้ขาย\nERP Query: สอบถามข้อมูลจากระบบ ERP",
    )

    st.divider()
    st.markdown("**Sample questions**")
    if mode == "Contract Analysis":
        samples = [
            "สัญญาคอมพิวเตอร์โน้ตบุ๊กมีความเสี่ยงอะไรบ้าง",
            "สัญญาจัดหาวัสดุสำนักงานมีเงื่อนไขอะไรที่ต้องระวัง",
        ]
    else:
        samples = [
            "ข้อมูลผู้ขายของบริษัท ABC เทคโนโลยีเป็นอย่างไร",
            "ฝ่ายไอทีมีงบประมาณเหลืออีกเท่าไหร่",
            "ใบสั่งซื้อ PO2024001 อยู่ในสถานะอะไร",
        ]

    for s in samples:
        if st.button(s, use_container_width=True, key=s):
            st.session_state["prefill"] = s

    st.divider()
    st.caption(f"Project: `{config.PROJECT_ID}`")
    st.caption(f"Model: `{config.GEMINI_MODEL}`")

# ── Main ──────────────────────────────────────────────────────────────────────

st.markdown("## Procurement Intelligence Agent")
st.markdown(
    '<span class="tag">Multi-Agent</span>'
    '<span class="tag">RAG</span>'
    '<span class="tag">LangGraph</span>'
    '<span class="tag">MCP</span>',
    unsafe_allow_html=True,
)
st.markdown("")

# Input
prefill = st.session_state.pop("prefill", "")
query = st.text_input(
    "Enter your query",
    value=prefill,
    placeholder="ถามเรื่องสัญญา ความเสี่ยงผู้ขาย หรือข้อมูล ERP...",
    label_visibility="collapsed",
)

run_btn = st.button("▶ Analyze", type="primary", use_container_width=False)

# ── Run ───────────────────────────────────────────────────────────────────────

if run_btn and query.strip():
    client = get_client()

    if mode == "Contract Analysis":
        collection = get_collection(client)
        tracer = Tracer()
        graph = build_graph(client, collection, config, tracer=tracer)

        with st.spinner("Agents working..."):
            result = graph.invoke({"query": query})

        # Summary
        st.markdown("### Executive Summary")
        st.markdown(
            f'<div class="summary-box"><p>{result["final_summary"]}</p></div>',
            unsafe_allow_html=True,
        )
        st.markdown("")

        # Metrics
        if tracer.records:
            total_cost = sum(r["estimated_cost_usd"] or 0 for r in tracer.records)
            total_latency = sum(r["latency_sec"] for r in tracer.records)
            total_tokens = sum((r["input_tokens"] or 0) + (r["output_tokens"] or 0) for r in tracer.records)

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Latency", f"{total_latency:.1f}s")
            col2.metric("Total Tokens", f"{total_tokens:,}")
            col3.metric("Est. Cost", f"${total_cost:.5f}")

            st.markdown("### Agent Trace")
            for r in tracer.records:
                st.markdown(
                    f'<div class="trace-row">'
                    f'<span class="trace-node">{r["node"]}</span>'
                    f'<span class="trace-stat">'
                    f'⏱ {r["latency_sec"]}s &nbsp;·&nbsp; '
                    f'↑{r["input_tokens"]} ↓{r["output_tokens"]} tokens &nbsp;·&nbsp; '
                    f'${r["estimated_cost_usd"]}'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )

    else:  # ERP Query
        with st.spinner("Querying ERP system..."):
            result = run_erp_query(client, query, config)

        st.markdown("### ERP Response")
        st.markdown(
            f'<div class="summary-box"><p>{result}</p></div>',
            unsafe_allow_html=True,
        )

elif run_btn and not query.strip():
    st.warning("กรุณาใส่คำถามก่อนกด Analyze")
