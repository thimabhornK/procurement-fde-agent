# Procurement FDE Agent

โปรเจกต์สาธิตระบบ multi-agent สำหรับหน่วยงานจัดซื้อ 

## ปัญหาที่แก้

หน่วยงานจัดซื้อทั่วไปเจอปัญหา: ตรวจสัญญาด้วยมือช้าและเสี่ยงพลาดเงื่อนไขผิดปกติ, ประเมิน
ความเสี่ยงผู้ขายใช้เวลานาน, และผู้บริหารต้องการสรุปที่เข้าใจง่ายไม่ใช่ตารางดิบ

## สถาปัตยกรรม

```
คำถามผู้ใช้
    ↓
Orchestrator (orchestrator.py)
    ↓
1. Document RAG agent  → ค้นสัญญาที่เกี่ยวข้องจาก embedding
2. Contract agent       → วิเคราะห์เงื่อนไขเสี่ยง + ตรวจสอบตัวเองอีกรอบ (self-reflection)
3. Vendor agent         → ประเมินความเสี่ยงผู้ขายจากประวัติ
    ↓
สรุปผู้บริหารภาษาไทย
```

## โครงสร้างไฟล์

```
procurement-fde-agent/
  config.py              ตั้งค่า project, model
  main.py                จุดเริ่มต้นรันโปรเจกต์
  orchestrator.py        ตัวแจกจ่ายงานให้ agent ย่อย
  agents/
    document_agent.py    ทำ embedding และค้นหาเอกสาร (RAG)
    contract_agent.py    วิเคราะห์ความเสี่ยงสัญญา
    vendor_agent.py      ประเมินความเสี่ยงผู้ขาย
  data/
    sample_data.py       ข้อมูลสัญญาและประวัติผู้ขายจำลอง
```

## วิธีติดตั้งและรัน

1. ติดตั้ง dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. ล็อกอิน Google Cloud (ทำครั้งเดียว):
   ```bash
   gcloud auth application-default login
   ```

3. แก้ `config.py` ให้ `PROJECT_ID` ตรงกับ Google Cloud project ของคุณ

4. รัน:
   ```bash
   python3 main.py
   ```

## ขั้นต่อไปที่วางแผนไว้ (ยังไม่ได้ทำ)

- [ ] ย้าย orchestrator จาก Python ธรรมดา ไปใช้ LangGraph หรือ Google ADK
- [ ] เพิ่ม evaluation pipeline วัดความแม่นยำด้วย golden dataset
- [ ] เพิ่ม tracing วัด latency, tokens/sec, cost-per-request
- [ ] เปลี่ยนจาก in-memory index เป็น Vertex AI Vector Search จริง
- [ ] สร้าง MCP server จำลองการต่อ ERP
- [ ] ทำ frontend เบาๆ (Streamlit) ให้ upload เอกสารแล้วเห็นผลแบบ real-time

## หมายเหตุ

Vertex AI ถูกเปลี่ยนชื่อเป็น "Gemini Enterprise Agent Platform" ตั้งแต่กลางปี 2026
โค้ดในโปรเจกต์นี้ยังใช้พารามิเตอร์ `vertexai=True` ซึ่งยังใช้งานได้ตามปกติ
