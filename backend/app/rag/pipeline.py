from __future__ import annotations
import os
import re
import chromadb
from openai import OpenAI
from pathlib import Path

CHROMA_PATH = Path(__file__).parent.parent.parent / "data" / "chroma"
COLLECTION_NAME = "destiny_lore"
EMBED_MODEL = "text-embedding-3-small"
TOP_K = 8

_chroma: chromadb.PersistentClient | None = None
_collection = None
_openai: OpenAI | None = None


def _get_collection():
    global _chroma, _collection
    if _collection is None:
        _chroma = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = _chroma.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _get_openai():
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _openai


def _keyword_hits(collection, question: str) -> list[dict]:
    """Direct substring search for entity names, ordered by specificity (rarest terms first)."""
    stop = {"what", "where", "when", "who", "which", "does", "from", "about",
            "tell", "know", "have", "would", "could", "should", "between",
            "fight", "battle", "origin", "story", "lore", "game", "that", "this",
            "with", "your", "their", "them", "were", "been", "will", "able",
            "team", "make", "made", "just", "also", "some", "more", "most",
            "beat", "kill", "killed", "defeat", "defeated", "using", "help"}

    words = re.findall(r"[A-Za-z']+", question)
    candidates = [w for w in words if len(w) >= 4 and w.lower() not in stop]

    # Score each candidate by how many documents match — fewer = more specific
    scored: list[tuple[int, str]] = []
    for term in candidates:
        try:
            count_result = collection.get(
                where_document={"$contains": term.title()},
                include=[],
            )
            count = len(count_result["ids"])
        except Exception:
            count = 999
        if count > 0:
            scored.append((count, term))

    # Most specific terms first; skip if they match too many docs (generic words)
    scored.sort(key=lambda x: x[0])
    specific = [(c, t) for c, t in scored if c <= 600]

    seen_ids: set[str] = set()
    hits: list[dict] = []

    for _, term in specific:
        try:
            results = collection.get(
                where_document={"$contains": term.title()},
                include=["documents", "metadatas"],
                limit=4,
            )
        except Exception:
            continue
        for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                hits.append({"text": doc, "name": meta.get("name", ""), "hash": meta.get("hash", "")})

    return hits


def retrieve(question: str, top_k: int = TOP_K) -> list[dict]:
    """Hybrid retrieval: keyword name-match hits first, then vector search to fill remaining slots."""
    collection = _get_collection()

    if collection.count() == 0:
        return []

    # 1. Direct keyword hits for named entities
    keyword_results = _keyword_hits(collection, question)
    seen_ids = {r["hash"] for r in keyword_results}

    # 2. Vector search for remaining slots
    client = _get_openai()
    response = client.embeddings.create(model=EMBED_MODEL, input=[question])
    query_embedding = response.data[0].embedding

    n = min(top_k + len(keyword_results), collection.count())
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n,
        include=["documents", "metadatas"],
    )

    vector_results = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        h = meta.get("hash", "")
        if h not in seen_ids:
            seen_ids.add(h)
            vector_results.append({"text": doc, "name": meta.get("name", ""), "hash": h})

    combined = keyword_results + vector_results
    return combined[:top_k]
