"""
Evaluation pipeline อย่างง่าย
ทดสอบว่า agent จับเงื่อนไขเสี่ยงที่ "ควรจับได้" จริงหรือไม่ โดยเทียบกับคำตอบที่รู้ล่วงหน้า
(เรียกว่า golden dataset) พร้อมพิมพ์ trace summary ของทั้งชุดทดสอบ

รันด้วยคำสั่ง: python3 evaluation.py
"""

from google import genai

import config
from agents import document_agent
from data.sample_data import CONTRACTS
from orchestrator_langgraph import build_graph
from utils.tracing import Tracer


# แต่ละเคสคือคำถาม + คำสำคัญที่ agent "ควรพูดถึง" ถ้าวิเคราะห์ถูกต้อง
GOLDEN_DATASET = [
    {
        "query": "สัญญาคอมพิวเตอร์โน้ตบุ๊กมีความเสี่ยงอะไรบ้าง",
        "expected_keywords": ["ล่วงหน้า", "ต่ออายุ"],
    },
    {
        "query": "สัญญาจัดหาวัสดุสำนักงานมีเงื่อนไขอะไรที่ต้องระวัง",
        "expected_keywords": ["ค่าปรับ"],
    },
]


def run_evaluation():
    client = genai.Client(
        vertexai=True,
        project=config.PROJECT_ID,
        location=config.LOCATION,
    )

    index = document_agent.build_index(client, CONTRACTS, config)
    tracer = Tracer()
    graph = build_graph(client, index, config, tracer=tracer)

    passed = 0
    for case in GOLDEN_DATASET:
        result = graph.invoke({"query": case["query"]})
        combined_text = result["contract_analysis"] + result["final_summary"]

        found = [kw for kw in case["expected_keywords"] if kw in combined_text]
        is_pass = len(found) == len(case["expected_keywords"])
        passed += int(is_pass)

        status = "ผ่าน" if is_pass else "ไม่ผ่าน"
        print(f"[{status}] คำถาม: {case['query']}")
        print(f"  พบคำสำคัญ: {found} / ต้องการ: {case['expected_keywords']}\n")

    print(f"สรุปผลรวม: ผ่าน {passed}/{len(GOLDEN_DATASET)} เคส\n")
    print(tracer.summary())


if __name__ == "__main__":
    run_evaluation()
