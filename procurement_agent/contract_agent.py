"""Contract risk review: a first pass, a self-check pass, then grounding in code.

1. First pass: the model lists risks of the fixed types, quoting each clause.
2. Self-check: the model sees the contract and its own list again, removes
   risks the text does not support and adds ones it missed.
3. Grounding: code drops any risk whose quote is not in the contract.

The self-check costs one extra model call; `reflect=False` skips it, and the
evaluation can run both ways to show whether it pays for itself.
"""

from __future__ import annotations

import json

from procurement_agent.risks import RISK_SCHEMA, definitions_text, ground
from procurement_agent.tracing import Tracer

FIRST_PASS_SYSTEM = """คุณเป็นผู้ตรวจสัญญาจัดซื้อ ทำงานให้ฝ่ายผู้ซื้อ
หาเงื่อนไขในสัญญาที่ทำให้ผู้ซื้อเสียเปรียบ โดยใช้ประเภทความเสี่ยงตามรายการนี้เท่านั้น:
{definitions}

กติกา:
- clause ต้องคัดลอกจากสัญญาแบบคำต่อคำ ห้ามเรียบเรียงใหม่
- ถ้าเป็นความเสี่ยงจากการที่สัญญาไม่มีข้อกำหนด ให้ clause เป็นค่าว่าง
- ถ้าไม่มีความเสี่ยงตามรายการ ให้ส่ง risks เป็นรายการว่าง ห้ามเดา
- reason เขียนภาษาไทยสั้นๆ 1 ประโยค"""

REFLECTION_SYSTEM = """คุณเป็นผู้ตรวจทานงานตรวจสัญญาจัดซื้อ
ประเภทความเสี่ยงที่ใช้ได้:
{definitions}

ตรวจรายการความเสี่ยงฉบับร่างเทียบกับสัญญา:
1. ตัดรายการที่ข้อความในสัญญาไม่ได้สนับสนุน หรือไม่ตรงกับนิยามของประเภทนั้น
2. เพิ่มความเสี่ยงตามนิยามที่ฉบับร่างพลาดไป
3. clause ต้องคัดลอกจากสัญญาแบบคำต่อคำ
ส่งรายการฉบับสุดท้ายในรูปแบบเดิม"""


def review_contract(llm, contract_text: str, tracer: Tracer | None = None,
                    reflect: bool = True) -> dict:
    system = FIRST_PASS_SYSTEM.format(definitions=definitions_text())
    draft = llm.generate_json("contract_first_pass", system, f"สัญญา:\n{contract_text}",
                              RISK_SCHEMA, tracer)
    final = draft
    if reflect:
        prompt = (f"สัญญา:\n{contract_text}\n\nฉบับร่าง:\n"
                  f"{json.dumps(draft, ensure_ascii=False, indent=1)}")
        final = llm.generate_json(
            "contract_self_check", REFLECTION_SYSTEM.format(definitions=definitions_text()),
            prompt, RISK_SCHEMA, tracer,
        )
    kept, dropped = ground(final.get("risks", []), contract_text)
    return {
        "risks": kept,
        "dropped": dropped,
        "first_pass_types": sorted({r.get("type") for r in draft.get("risks", [])}),
    }
