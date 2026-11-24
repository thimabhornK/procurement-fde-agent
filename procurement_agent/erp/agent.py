"""Answer ERP questions: Gemini picks a tool by function calling, code runs it,
and Gemini words the answer from the tool result only."""

from __future__ import annotations

import json

from procurement_agent.erp import tools
from procurement_agent.tracing import Tracer

SELECT_SYSTEM = "คุณช่วยฝ่ายจัดซื้อดูข้อมูลจากระบบ ERP เรียก tool ที่ตอบคำถามได้"
ANSWER_SYSTEM = """ตอบคำถามเป็นภาษาไทยสั้นๆ จากผลลัพธ์ของระบบ ERP เท่านั้น
ห้ามเพิ่มตัวเลขที่ไม่มีในผลลัพธ์ ถ้าไม่พบข้อมูลให้บอกตรงๆ"""


def answer(llm, question: str, tracer: Tracer | None = None) -> dict:
    calls = llm.choose_tools("erp_choose_tool", SELECT_SYSTEM, question,
                             tools.DECLARATIONS, tracer)
    results = [{"tool": name, "args": args, "result": tools.call(name, args)}
               for name, args in calls]
    if not results:
        return {"calls": [], "answer": "คำถามนี้ไม่ต้องใช้ข้อมูลจากระบบ ERP หรือระบบไม่มีข้อมูลที่ตรงกัน"}
    prompt = (f"คำถาม: {question}\n\nผลลัพธ์จาก ERP:\n"
              f"{json.dumps(results, ensure_ascii=False, indent=1)}")
    text = llm.generate_text("erp_answer", ANSWER_SYSTEM, prompt, tracer)
    return {"calls": results, "answer": text}
