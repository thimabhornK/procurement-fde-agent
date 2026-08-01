"""
Document RAG agent
หน้าที่: แปลงเอกสารเป็น embedding แล้วค้นหาเอกสารที่เกี่ยวข้องกับคำถาม
นี่คือ RAG แบบพื้นฐานที่สุด ทำเองโดยไม่พึ่ง vector database ภายนอก
เพื่อให้เห็นกลไกเบื้องหลังชัดเจนก่อนค่อยเปลี่ยนไปใช้ Vector Search จริงทีหลัง
"""

import numpy as np


def get_embedding(client, text: str, config) -> np.ndarray:
    """แปลงข้อความให้เป็นชุดตัวเลข (embedding) ที่บอกความหมาย"""
    result = client.models.embed_content(
        model=config.EMBEDDING_MODEL,
        contents=text,
    )
    return np.array(result.embeddings[0].values)


def build_index(client, documents: list, config) -> list:
    """สร้าง index โดยแปลงเอกสารทุกฉบับเป็น embedding เก็บไว้ในหน่วยความจำ"""
    index = []
    for doc in documents:
        embedding = get_embedding(client, doc["text"], config)
        index.append({"doc": doc, "embedding": embedding})
    return index


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """วัดความใกล้เคียงของความหมายระหว่างเวกเตอร์สองตัว ยิ่งใกล้ 1 ยิ่งเกี่ยวข้องกันมาก"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def retrieve(client, index: list, query: str, config, top_k: int = 1) -> list:
    """ค้นหาเอกสารที่เกี่ยวข้องที่สุดกับคำถามที่ถาม"""
    query_embedding = get_embedding(client, query, config)
    scored = [
        (cosine_similarity(query_embedding, item["embedding"]), item["doc"])
        for item in index
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]
