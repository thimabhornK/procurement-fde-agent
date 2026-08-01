"""
จุดเริ่มต้นรันโปรเจกต์ Procurement FDE Agent
รันด้วยคำสั่ง: python3 main.py
"""

from google import genai

import config
from agents import document_agent
from data.sample_data import CONTRACTS
import orchestrator


def main():
    client = genai.Client(
        vertexai=True,
        project=config.PROJECT_ID,
        location=config.LOCATION,
    )

    print("กำลังสร้าง index จากเอกสารตัวอย่าง...")
    index = document_agent.build_index(client, CONTRACTS, config)
    print(f"สร้าง index สำเร็จ {len(index)} เอกสาร\n")

    query = "สัญญาคอมพิวเตอร์โน้ตบุ๊กมีความเสี่ยงอะไรบ้าง ควรอนุมัติไหม"
    print(f"คำถาม: {query}\n")

    result = orchestrator.run(client, index, query, config)
    print("=== สรุปผู้บริหาร ===")
    print(result)


if __name__ == "__main__":
    main()
