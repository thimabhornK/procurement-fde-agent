"""
Orchestrator เวอร์ชัน LangGraph
ทำงานเหมือน orchestrator.py เดิมทุกอย่าง เปลี่ยนแค่วิธีจัดการการส่งต่องาน
จาก Python ธรรมดา มาเป็น StateGraph ของ LangGraph

concept:
- state คือ "กระดานไวท์บอร์ด" ที่ agent แต่ละตัวอ่านและเขียนเพิ่ม
- node คือ agent แต่ละตัว (ฟังก์ชันที่รับ state แล้วคืนค่าที่จะอัปเดตลงไป)
- edge คือเส้นบอกว่า agent ไหนทำงานต่อจากไหน
"""

from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from agents import document_agent, contract_agent, vendor_agent
from data.sample_data import VENDOR_HISTORY


class AgentState(TypedDict):
    query: str
    vendor_name: Optional[str]
    contract_text: Optional[str]
    contract_analysis: Optional[str]
    vendor_analysis: Optional[str]
    final_summary: Optional[str]


def build_graph(client, index, config):
    """สร้างและคอมไพล์กราฟ ต้องส่ง client/index/config เข้ามาผูกไว้กับแต่ละ node"""

    def retrieve_node(state: AgentState) -> dict:
        docs = document_agent.retrieve(client, index, state["query"], config, top_k=1)
        contract = docs[0]
        return {"contract_text": contract["text"], "vendor_name": contract["vendor"]}

    def contract_node(state: AgentState) -> dict:
        analysis = contract_agent.analyze_contract(client, state["contract_text"], config)
        return {"contract_analysis": analysis}

    def vendor_node(state: AgentState) -> dict:
        vendor_name = state["vendor_name"]
        if vendor_name in VENDOR_HISTORY:
            analysis = vendor_agent.score_vendor(
                client, vendor_name, VENDOR_HISTORY[vendor_name], config
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

        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
        )
        return {"final_summary": response.text}

    # ประกอบกราฟ: บอกว่ามี node อะไรบ้าง แล้วต่อเส้นทางกันยังไง
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
