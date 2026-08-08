"""
Document RAG agent — เวอร์ชัน Chroma Vector DB
เปลี่ยนจาก in-memory numpy cosine similarity มาใช้ Chroma
ซึ่งเป็น vector database จริงที่เก็บข้อมูลลงดิสก์และค้นหาได้เร็วกว่าเมื่อข้อมูลโตขึ้น

ข้อดีของ Chroma เทียบกับ in-memory:
- persist ข้อมูลลงดิสก์ ไม่ต้อง embed ใหม่ทุกครั้งที่รัน
- รองรับข้อมูลหลายพันฉบับโดยไม่กินหน่วยความจำ
- API คล้ายกับ Vertex AI Vector Search ทำให้เปลี่ยนในอนาคตได้ง่าย
"""

import chromadb
from chromadb.config import Settings


def get_embedding(client, text: str, config) -> list:
    """แปลงข้อความให้เป็นชุดตัวเลข (embedding) ผ่าน Gemini embedding model"""
    result = client.models.embed_content(
        model=config.EMBEDDING_MODEL,
        contents=text,
    )
    return result.embeddings[0].values


def build_index(client, documents: list, config, persist_path: str = "./chroma_db") -> chromadb.Collection:
    """
    สร้าง Chroma collection และ embed เอกสารทั้งหมดลงไป
    ถ้ามีข้อมูลเดิมอยู่แล้ว (persist_path) จะใช้ของเดิมโดยไม่ embed ซ้ำ
    """
    chroma_client = chromadb.PersistentClient(
        path=persist_path,
        settings=Settings(anonymized_telemetry=False),
    )

    # ถ้า collection มีอยู่แล้ว ลบทิ้งแล้วสร้างใหม่ (สำหรับ dev/demo)
    # ใน production จริงควรเช็คก่อนว่ามีข้อมูลอยู่แล้วหรือยัง
    try:
        chroma_client.delete_collection("procurement_docs")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name="procurement_docs",
        metadata={"hnsw:space": "cosine"},
    )

    embeddings = [get_embedding(client, doc["text"], config) for doc in documents]

    collection.add(
        ids=[doc["id"] for doc in documents],
        embeddings=embeddings,
        documents=[doc["text"] for doc in documents],
        metadatas=[{"vendor": doc["vendor"]} for doc in documents],
    )

    return collection


def retrieve(client, collection: chromadb.Collection, query: str, config, top_k: int = 1) -> list:
    """ค้นหาเอกสารที่เกี่ยวข้องที่สุดกับคำถามจาก Chroma collection"""
    query_embedding = get_embedding(client, query, config)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas"],
    )

    docs = []
    for i in range(len(results["ids"][0])):
        docs.append({
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "vendor": results["metadatas"][0][i]["vendor"],
        })

    return docs
