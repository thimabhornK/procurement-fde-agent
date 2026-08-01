"""
Vendor scoring agent
หน้าที่: ประเมินความเสี่ยงผู้ขายจากประวัติการทำงานร่วมกันที่ผ่านมา
"""


def score_vendor(client, vendor_name: str, vendor_data: dict, config) -> str:
    prompt = f"""คุณคือนักวิเคราะห์ความเสี่ยงผู้ขาย ประเมินผู้ขายรายนี้:

ชื่อผู้ขาย: {vendor_name}
เป็นผู้ขายมาแล้ว: {vendor_data['years_as_vendor']} ปี
ส่งมอบล่าช้าปีที่แล้ว: {vendor_data['late_deliveries_last_year']} ครั้ง จาก {vendor_data['total_orders_last_year']} ออเดอร์
เงื่อนไขการชำระเงินที่ขอ: {vendor_data['payment_terms_requested']}

ให้คะแนนความเสี่ยง 1-10 (10 คือเสี่ยงสูงสุด) พร้อมเหตุผลสั้นๆ 2-3 ข้อ"""

    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
    )
    return response.text
