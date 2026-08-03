"""
Contract risk agent
หน้าที่: อ่านสัญญา หาเงื่อนไขที่น่ากังวล แล้วตรวจสอบตัวเองอีกรอบ (self-reflection)
ก่อนสรุปผล เพื่อลดโอกาสตอบพลาดหรือมั่นใจในสิ่งที่ไม่สำคัญมากเกินไป
"""

from utils import tracing


def analyze_contract(client, contract_text: str, config, tracer=None) -> str:
    # รอบแรก: วิเคราะห์เบื้องต้น
    first_pass = tracing.generate(
        client,
        config,
        contents=f"""คุณคือผู้เชี่ยวชาญด้านกฎหมายจัดซื้อ อ่านสัญญานี้แล้วระบุเงื่อนไขที่น่ากังวล
เช่น การชำระเงินล่วงหน้าเต็มจำนวน, การต่ออายุอัตโนมัติ, ค่าปรับที่ไม่สมเหตุสมผล

สัญญา:
{contract_text}

ตอบเป็นรายการข้อๆ สั้นๆ""",
        node_name="contract_first_pass",
        tracer=tracer,
    )

    # รอบสอง: ตรวจสอบตัวเองอีกครั้ง (self-reflection pattern)
    reflection = tracing.generate(
        client,
        config,
        contents=f"""นี่คือผลการวิเคราะห์สัญญาที่คุณเพิ่งทำ:

{first_pass.text}

ตรวจสอบอีกครั้งว่า:
1. มีเงื่อนไขเสี่ยงข้อไหนที่พลาดไปหรือไม่
2. มีข้อไหนที่ประเมินเกินจริงหรือไม่สำคัญพอจะเป็นความเสี่ยงหรือไม่

ให้คำตอบสุดท้ายที่ผ่านการตรวจทานแล้ว เป็นรายการข้อๆ""",
        node_name="contract_reflection",
        tracer=tracer,
    )

    return reflection.text
