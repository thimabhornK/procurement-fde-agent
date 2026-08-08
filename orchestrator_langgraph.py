"""
Orchestrator เวอร์ชัน LangGraph + Chroma
อัปเดตให้รับ Chroma collection แทน in-memory index list
"""

from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from agents import document_agent, contract_agent, vendor_agent
from data.sample_data import VENDOR_HISTORY
from utils import tracing


class AgentState(TypedDict):
    query: str
    vendor_name: Optional[str]
    contract_text: Optional[str]
    contract_analysis: Optional[str]
    vendor_analysis: Optional[str]
    final_summary: Optional[str]


def build_graph(client, collection, config, tracer=None):
    """รับ Chroma collection แทน index list"""

    def retrieve_node(state: AgentState) -> dict:
        docs = document_agent.retrieve(client, collection, state["query"], config, top_k=1)
        contract = docs[0]
        return {"contract_text": contract["text"], "vendor_name": contract["vendor"]}

    def contract_node(state: AgentState) -> dict:
        analysis = contract_agent.analyze_contract(
            client, state["contract_text"], config, tracer=tracer
        )
        return {"contract_analysis": analysis}

    def vendor_node(state: AgentState) -> dict:
        vendor_name = state["vendor_name"]
        if vendor_name in VENDOR_HISTORY:
            analysis = vendor_agent.score_vendor(
                client, vendor_name, VENDOR_HISTORY[vendor_name], config, tracer=tracer
            )
        else:
            analysis = "ไม่มีข้อมูลประวัติผู้ขายรายนี้ในระบบ"
        return {"vendor_analysis": analysis}

    def summary_node(state: AgentState) -> dict:
        prompt = f"""สรุปให้ผู้บริหารฟังแบบเข้าใจง่าย ไม่ใช้ศัพท์เทคนิค จากข้อมูลนี้:

คำถามที่ถูกถาม: {state['query']}

ผลวิเคราะห์สัญญา ({state['vendor_name']}):
{state['contract_analysis']}

ผลประเมินความเสี่ยงผู้ขาย:
{state['vendor_analysis']}

สรุปเป็นย่อหน้าสั้นๆ 3-4 ประโยค พร้อมคำแนะนำว่าควรอนุมัติหรือควรเจรจาต่อรองก่อน"""

        response = tracing.generate(
            client, config, contents=prompt, node_name="executive_summary", tracer=tracer
        )
        return {"final_summary": response.text}

    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("analyze_contract", contract_node)
    graph.add_node("score_vendor", vendor_node)
    graph.add_node("summarize", summary_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "analyze_contract")
    graph.add_edge("analyze_contract", "score_vendor")
    graph.add_edge("score_vendor", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()
