"""
ทดสอบ MCP server เชื่อมต่อ ERP
รันด้วยคำสั่ง: python3 main_mcp.py
"""

from google import genai

import config
from mcp.erp_agent import run_erp_query


def main():
    client = genai.Client(
        vertexai=True,
        project=config.PROJECT_ID,
        location=config.LOCATION,
    )

    # ทดสอบ 3 คำถามที่ครอบคลุม tool แต่ละตัว
    queries = [
        "ข้อมูลผู้ขายของบริษัท ABC เทคโนโลยีในระบบเป็นอย่างไร",
        "ฝ่ายไอทีมีงบประมาณเหลืออีกเท่าไหร่",
        "ใบสั่งซื้อ PO2024001 ตอนนี้อยู่ในสถานะอะไร",
    ]

    for query in queries:
        print(f"คำถาม: {query}")
        result = run_erp_query(client, query, config)
        print(f"คำตอบ: {result}")
        print("-" * 60)


if __name__ == "__main__":
    main()
