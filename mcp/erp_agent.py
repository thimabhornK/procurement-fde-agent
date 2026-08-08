"""
ERP MCP agent
ให้ Gemini ตัดสินใจเองว่าต้องเรียก tool ไหนจาก ERP server
นี่คือ "agentic tool use" ที่ต่างจาก RAG ตรงที่ agent ไม่ได้แค่ค้นหา
แต่ตัดสินใจเรียก action จากระบบภายนอก

flow:
1. ส่งคำถาม + รายการ tool ที่มีให้ Gemini
2. Gemini ตัดสินใจว่าต้องเรียก tool ไหน และส่ง arguments อะไร
3. เราเรียก tool นั้นจาก ERP server จริง
4. ส่งผลลัพธ์กลับให้ Gemini สรุป
"""

import json
from mcp.erp_server import TOOLS, call_tool


def run_erp_query(client, query: str, config) -> str:
    """
    รัน query ผ่าน MCP pattern:
    Gemini เลือก tool → เราเรียก ERP server → Gemini สรุปผล
    """

    # รอบที่ 1: ให้ Gemini อ่านคำถามและเลือก tool ที่เหมาะสม
    tool_selection_prompt = f"""คุณมีเครื่องมือเชื่อมต่อระบบ ERP ดังนี้:

{json.dumps(TOOLS, ensure_ascii=False, indent=2)}

คำถาม: {query}

ตอบใน JSON format เท่านั้น ไม่มีข้อความอื่น:
{{
  "tool_name": "ชื่อ tool ที่จะใช้",
  "tool_input": {{ "parameter": "value" }}
}}

ถ้าไม่ต้องใช้ tool ใดเลย ให้ตอบว่า:
{{
  "tool_name": null,
  "tool_input": {{}}
}}"""

    selection_response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=tool_selection_prompt,
    )

    # แปลง JSON response จาก Gemini
    raw = selection_response.text.strip()
    # ลบ markdown code block ถ้ามี
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    tool_decision = json.loads(raw.strip())

    tool_name = tool_decision.get("tool_name")
    tool_input = tool_decision.get("tool_input", {})

    # ถ้า Gemini เลือก tool ให้เรียก ERP server
    erp_result = None
    if tool_name:
        erp_result = call_tool(tool_name, tool_input)

    # รอบที่ 2: ให้ Gemini สรุปผลลัพธ์จาก ERP เป็นภาษาที่อ่านง่าย
    summary_prompt = f"""คำถามเดิม: {query}

{"ผลลัพธ์จากระบบ ERP:" if erp_result else "ไม่ได้เรียกใช้ระบบ ERP"}
{json.dumps(erp_result, ensure_ascii=False, indent=2) if erp_result else ""}

สรุปคำตอบสั้นๆ เป็นภาษาไทยที่เข้าใจง่าย ไม่ต้องใช้ศัพท์เทคนิค"""

    final_response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=summary_prompt,
    )

    return final_response.text
