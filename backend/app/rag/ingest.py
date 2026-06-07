"""
Run once (or whenever you want to re-index):
    python -m app.rag.ingest
from the backend/ directory with the venv active.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import chromadb
from openai import OpenAI

# Insert project root so `app.*` imports work when run directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.bungie.manifest import ManifestManager

CHROMA_PATH = Path(__file__).parent.parent.parent / "data" / "chroma"
COLLECTION_NAME = "destiny_lore"
EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100


def _lore_document(entry: dict) -> tuple[str, str, dict] | None:
    display = entry.get("displayProperties", {})
    name = (display.get("name") or "").strip()
    description = (display.get("description") or "").strip()
    subtitle = (entry.get("subtitle") or "").strip()
    doc_id = str(entry.get("hash", ""))

    parts = [p for p in [name, subtitle, description] if p]
    if not parts:
        return None
    return doc_id, "\n".join(parts), {"hash": doc_id, "name": name, "subtitle": subtitle}


def _item_document(entry: dict) -> tuple[str, str, dict] | None:
    display = entry.get("displayProperties", {})
    name = (display.get("name") or "").strip()
    flavor = (entry.get("flavorText") or "").strip()
    item_hash = str(entry.get("hash", ""))
    doc_id = f"item_{item_hash}"

    if not flavor:
        return None
    text = f"{name}\n{flavor}" if name else flavor
    return doc_id, text, {"hash": doc_id, "name": name, "subtitle": flavor[:120]}


def _activity_document(entry: dict) -> tuple[str, str, dict] | None:
    display = entry.get("displayProperties", {})
    name = (display.get("name") or "").strip()
    description = (display.get("description") or "").strip()
    activity_hash = str(entry.get("hash", ""))
    doc_id = f"activity_{activity_hash}"

    if not description:
        return None
    text = f"{name}\n{description}" if name else description
    return doc_id, text, {"hash": doc_id, "name": name, "subtitle": description[:120]}


def _season_document(entry: dict) -> tuple[str, str, dict] | None:
    display = entry.get("displayProperties", {})
    name = (display.get("name") or "").strip()
    description = (display.get("description") or "").strip()
    season_hash = str(entry.get("hash", ""))
    doc_id = f"season_{season_hash}"

    if not description:
        return None
    text = f"{name}\n{description}" if name else description
    return doc_id, text, {"hash": doc_id, "name": name, "subtitle": description[:120]}


async def _collect_docs(manifest: ManifestManager) -> list[tuple[str, str, dict]]:
    docs: list[tuple[str, str, dict]] = []

    print("Loading DestinyLoreDefinition...")
    for row in await manifest.get_all_lore():
        try:
            result = _lore_document(json.loads(row))
            if result:
                docs.append(result)
        except Exception:
            continue
    print(f"  {len(docs)} lore entries")

    before = len(docs)
    print("Loading item flavor text...")
    for row in await manifest.get_all_items_with_flavor():
        try:
            result = _item_document(json.loads(row))
            if result:
                docs.append(result)
        except Exception:
            continue
    print(f"  {len(docs) - before} item flavor entries")

    before = len(docs)
    print("Loading activity descriptions...")
    for row in await manifest.get_all_activities_with_description():
        try:
            result = _activity_document(json.loads(row))
            if result:
                docs.append(result)
        except Exception:
            continue
    print(f"  {len(docs) - before} activity entries")

    before = len(docs)
    print("Loading season descriptions...")
    for row in await manifest.get_all_seasons():
        try:
            result = _season_document(json.loads(row))
            if result:
                docs.append(result)
        except Exception:
            continue
    print(f"  {len(docs) - before} season entries")

    return docs


async def ingest():
    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    manifest = ManifestManager()
    await manifest.init_manifest()

    docs = await _collect_docs(manifest)
    print(f"Total: {len(docs)} documents")

    existing_ids = set(collection.get(include=[])["ids"])
    docs = [d for d in docs if d[0] not in existing_ids]
    print(f"{len(docs)} new entries to embed")

    if not docs:
        print("Nothing to embed — collection is up to date.")
        return

    total = len(docs)
    for i in range(0, total, BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        ids = [d[0] for d in batch]
        texts = [d[1] for d in batch]
        metadatas = [d[2] for d in batch]

        response = openai_client.embeddings.create(model=EMBED_MODEL, input=texts)
        embeddings = [item.embedding for item in response.data]

        collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        print(f"  Embedded {min(i + BATCH_SIZE, total)}/{total}", end="\r")

    print(f"\nDone. {total} new entries indexed into ChromaDB at {CHROMA_PATH}")


if __name__ == "__main__":
    asyncio.run(ingest())
