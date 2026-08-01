from google import genai

client = genai.Client(
    vertexai=True,
    project="procurement-fde-agent",
    location="us-central1"
)

# ตัวอย่างเอกสารจำลอง (ใบขอซื้อ)
purchase_request = """
เรื่อง: ขอซื้อคอมพิวเตอร์โน้ตบุ๊ก จำนวน 15 เครื่อง
งบประมาณ: 750,000 บาท
ผู้ขาย: บริษัท ABC เทคโนโลยี จำกัด
เงื่อนไข: ชำระเงิน 100% ล่วงหน้า, รับประกัน 1 ปี
กำหนดส่งมอบ: 30 วันหลังอนุมัติ
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=f"อ่านใบขอซื้อนี้แล้วช่วยระบุจุดที่น่ากังวล:\n\n{purchase_request}"
)

print(response.text)