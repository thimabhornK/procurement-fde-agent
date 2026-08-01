"""
Orchestrator
หน้าที่: รับคำถามจากผู้ใช้ แล้วมอบหมายงานให้ agent ย่อยที่เกี่ยวข้องตามลำดับ
จากนั้นรวมผลลัพธ์ทั้งหมดเป็นสรุปผู้บริหารภาษาไทย

นี่คือ orchestrator แบบง่ายที่สุด เขียนเป็นฟังก์ชัน Python ตรงๆ
ยังไม่ใช้ framework อย่าง LangGraph หรือ ADK เพื่อให้เห็น logic การมอบหมายงานชัดเจนก่อน
"""

from agents import document_agent, contract_agent, vendor_agent
from data.sample_data import VENDOR_HISTORY


def run(client, index, query: str, config) -> str:
    # ขั้น 1: มอบหมายให้ document agent ค้นหาสัญญาที่เกี่ยวข้องที่สุด
    relevant_docs = document_agent.retrieve(client, index, query, config, top_k=1)
    contract = relevant_docs[0]

    # ขั้น 2: มอบหมายให้ contract agent วิเคราะห์ความเสี่ยงของสัญญา
    contract_analysis = contract_agent.analyze_contract(client, contract["text"], config)

    # ขั้น 3: มอบหมายให้ vendor agent ประเมินความเสี่ยงผู้ขาย (ถ้ามีข้อมูลประวัติ)
    vendor_name = contract["vendor"]
    vendor_analysis = "ไม่มีข้อมูลประวัติผู้ขายรายนี้ในระบบ"
    if vendor_name in VENDOR_HISTORY:
        vendor_analysis = vendor_agent.score_vendor(
            client, vendor_name, VENDOR_HISTORY[vendor_name], config
        )

    # ขั้น 4: รวมผลจากทุก agent เป็นสรุปผู้บริหารภาษาไทย
    summary_prompt = f"""สรุปให้ผู้บริหารฟังแบบเข้าใจง่าย ไม่ใช้ศัพท์เทคนิค จากข้อมูลนี้:

คำถามที่ถูกถาม: {query}

ผลวิเคราะห์สัญญา ({vendor_name}):
{contract_analysis}

ผลประเมินความเสี่ยงผู้ขาย:
{vendor_analysis}

สรุปเป็นย่อหน้าสั้นๆ 3-4 ประโยค พร้อมคำแนะนำว่าควรอนุมัติหรือควรเจรจาต่อรองก่อน"""

    final_summary = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=summary_prompt,
    )
    return final_summary.text
