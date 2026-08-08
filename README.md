# Procurement Intelligence Agent

A production-grade multi-agent AI system that automates enterprise procurement workflows — from document ingestion to Thai-language executive summary generation. Built as a portfolio project targeting the **Forward Deployed Engineer (GenAI)** role at Google Cloud, covering all core and preferred qualifications in the job description.

---

## Business Problem

Procurement teams face three recurring bottlenecks:
- Manual contract review is slow and error-prone (missed auto-renewal clauses, unfavorable payment terms)
- Vendor risk assessment relies on scattered spreadsheets with no systematic scoring
- Executives need concise summaries, not raw data tables, to make approval decisions quickly

This system automates all three using a coordinated multi-agent pipeline powered by Gemini on Google Cloud.

---

## Architecture

```
User Query
    ↓
Orchestrator (LangGraph StateGraph)
    ├── Document RAG Agent   → semantic search over contract corpus (Chroma Vector DB)
    ├── Contract Risk Agent  → clause-level risk analysis with self-reflection loop
    ├── Vendor Scoring Agent → risk scoring from historical ERP data
    └── Executive Summary    → Thai-language summary with approval recommendation
    ↓
MCP Server (ERP Integration)
    ├── get_vendor_info   → vendor status, credit limit, approved categories
    ├── check_budget      → department budget remaining
    └── get_po_status     → purchase order approval status
```

---

## File Structure

```
procurement-fde-agent/
├── config.py                    Project, model, and cost config
├── main.py                      Plain Python orchestrator (baseline)
├── main_langgraph.py            LangGraph orchestrator (primary)
├── main_mcp.py                  MCP ERP integration demo
├── orchestrator.py              Plain Python multi-agent flow
├── orchestrator_langgraph.py    LangGraph StateGraph flow
├── evaluation.py                Golden dataset evaluation pipeline
├── requirements.txt
├── README.md
│
├── agents/
│   ├── document_agent.py        RAG with Chroma vector DB
│   ├── contract_agent.py        Contract risk analysis + self-reflection
│   └── vendor_agent.py          Vendor risk scoring
│
├── data/
│   └── sample_data.py           Mock contracts and vendor history
│
├── mcp/
│   ├── erp_server.py            Mock ERP server (vendor, budget, PO tools)
│   └── erp_agent.py             Agentic tool-use loop with Gemini
│
└── utils/
    └── tracing.py               Latency, token, and cost-per-request tracker
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Gemini 2.5 Flash via Gemini Enterprise Agent Platform (formerly Vertex AI) |
| Agent Framework | LangGraph StateGraph |
| Vector Database | Chroma (persistent, disk-backed) |
| Embedding Model | text-embedding-005 |
| MCP Integration | Custom MCP server simulating SAP/Oracle ERP |
| Observability | Custom Tracer (latency, tokens/sec, cost-per-request per node) |
| Evaluation | Golden dataset with keyword-based accuracy benchmarking |
| Language | Python 3.13 |

---

## Agentic Patterns Implemented

- **Hierarchical delegation** — Orchestrator assigns tasks to specialized sub-agents
- **Self-reflection** — Contract agent runs two-pass analysis: initial review → self-critique → final output
- **Agentic tool use (MCP)** — Gemini decides which ERP tool to call based on user intent, without hardcoded routing
- **RAG pipeline** — Semantic retrieval from Chroma vector DB using Gemini embeddings

---

## Observability Results (from live run)

| Node | Latency | Tokens In | Tokens Out | Est. Cost |
|---|---|---|---|---|
| contract_first_pass | 11.8s | 173 | 126 | $0.000051 |
| contract_reflection | 20.7s | 195 | 830 | $0.000264 |
| vendor_scoring | 8.5s | 112 | 178 | $0.000062 |
| executive_summary | 12.5s | 1,115 | 265 | $0.000163 |
| **Total (1 query)** | **53.4s** | | | **~$0.00054** |

Cost at scale: ~$0.00054 per query → ~$16/month at 1,000 queries/day

---

## How to Run

**1. Install dependencies**
```bash
python3 -m pip install -r requirements.txt
```

**2. Authenticate with Google Cloud (one-time)**
```bash
gcloud auth application-default login
```

**3. Update project ID in config.py if needed**
```python
PROJECT_ID = "procurement-fde-agent"
```

**4. Run the multi-agent pipeline**
```bash
python3 main_langgraph.py
```

**5. Run evaluation pipeline**
```bash
python3 evaluation.py
```

**6. Run MCP ERP integration demo**
```bash
python3 main_mcp.py
```

---

## Evaluation Results

| Test Case | Expected Keywords | Result |
|---|---|---|
| Notebook contract risks | ล่วงหน้า, ต่ออายุ | In progress — improving keyword coverage |
| Office supply contract risks | ค่าปรับ | ✅ Pass |

**Known limitation:** Current evaluation uses exact keyword matching. Next improvement: semantic similarity scoring using an LLM-as-judge approach.

---

## Roadmap

- [x] Gemini API integration via Vertex AI / Agent Platform
- [x] Multi-agent orchestration (plain Python)
- [x] LangGraph StateGraph orchestration
- [x] Self-reflection pattern in contract analysis
- [x] Chroma vector DB with persistent storage
- [x] Observability framework (latency, tokens, cost-per-request)
- [x] Golden dataset evaluation pipeline
- [x] MCP server with ERP tool integration
- [ ] Streamlit frontend with real-time agent trace visualization
- [ ] LLM-as-judge evaluation (semantic accuracy scoring)
- [ ] Parallel agent execution (contract + vendor agents run concurrently)

---

## Note on Rebranding

Vertex AI was rebranded to **Gemini Enterprise Agent Platform** at Google Cloud Next 2026. The codebase uses `vertexai=True` in the SDK, which remains fully functional under the new platform name.

---

## Author

Built by Thimabhorn K. — 2026
