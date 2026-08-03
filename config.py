"""
ตั้งค่ากลางของโปรเจกต์ Procurement FDE Agent
แก้ PROJECT_ID ให้ตรงกับ Google Cloud project ของคุณ ถ้าไม่ใช่ procurement-fde-agent
"""

PROJECT_ID = "procurement-fde-agent"
LOCATION = "us-central1"

GEMINI_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "text-embedding-005"

# ราคาโดยประมาณ (ดอลลาร์ต่อ 1,000 token) — เป็นตัวเลขตัวอย่างเท่านั้น
# ตรวจสอบราคาจริงล่าสุดที่ ai.google.dev/pricing หรือหน้า Cloud Billing ก่อนใช้งานจริง
COST_PER_1K_INPUT_TOKENS = 0.000075
COST_PER_1K_OUTPUT_TOKENS = 0.0003
