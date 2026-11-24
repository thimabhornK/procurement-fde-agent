"""Find the contract a question is about: Gemini embeddings in a Chroma collection.

All contracts are embedded in one batch call when the index is built. The
collection lives in memory unless a path is given.
"""

from __future__ import annotations

import uuid

from procurement_agent.tracing import Tracer


class ContractIndex:
    def __init__(self, llm, contracts: list[dict], persist_path: str | None = None,
                 tracer: Tracer | None = None) -> None:
        import chromadb
        from chromadb.config import Settings

        settings = Settings(anonymized_telemetry=False)
        client = (chromadb.PersistentClient(path=persist_path, settings=settings)
                  if persist_path else chromadb.EphemeralClient(settings=settings))
        self.llm = llm
        self.contracts = {c["id"]: c for c in contracts}
        self.collection = client.create_collection(
            name=f"contracts-{uuid.uuid4().hex[:8]}", metadata={"hnsw:space": "cosine"}
        )
        texts = [f"{c['title']}\n{c['text']}" for c in contracts]
        vectors = llm.embed(texts, "RETRIEVAL_DOCUMENT", tracer, node="embed_contracts")
        self.collection.add(
            ids=[c["id"] for c in contracts],
            embeddings=vectors,
            documents=texts,
            metadatas=[{"vendor_id": c["vendor_id"]} for c in contracts],
        )

    def search(self, query: str, k: int = 1, tracer: Tracer | None = None) -> list[dict]:
        [vector] = self.llm.embed([query], "RETRIEVAL_QUERY", tracer, node="embed_query")
        result = self.collection.query(query_embeddings=[vector], n_results=k,
                                       include=["distances"])
        return [
            {"contract": self.contracts[cid], "distance": round(dist, 4)}
            for cid, dist in zip(result["ids"][0], result["distances"][0], strict=True)
        ]
