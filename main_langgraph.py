"""
รันโปรเจกต์เวอร์ชัน LangGraph
รันด้วยคำสั่ง: python3 main_langgraph.py

เก็บ main.py เดิมไว้เป็นเวอร์ชันเปรียบเทียบ (ไม่ใช้ framework)
ไฟล์นี้คือเวอร์ชันที่ใช้ LangGraph จัดการ multi-agent workflow
"""

from google import genai

import config
from agents import document_agent
from data.sample_data import CONTRACTS
from orchestrator_langgraph import build_graph
from utils.tracing import Tracer


def main():
    client = genai.Client(
        vertexai=True,
        project=config.PROJECT_ID,
        location=config.LOCATION,
    )

    print("กำลังสร้าง index จากเอกสารตัวอย่าง...")
    index = document_agent.build_index(client, CONTRACTS, config)
    print(f"สร้าง index สำเร็จ {len(index)} เอกสาร\n")

    tracer = Tracer()
    graph = build_graph(client, index, config, tracer=tracer)

    query = "สัญญาคอมพิวเตอร์โน้ตบุ๊กมีความเสี่ยงอะไรบ้าง ควรอนุมัติไหม"
    print(f"คำถาม: {query}\n")

    result = graph.invoke({"query": query})

    print("=== สรุปผู้บริหาร ===")
    print(result["final_summary"])
    print()
    print(tracer.summary())


if __name__ == "__main__":
    main()
