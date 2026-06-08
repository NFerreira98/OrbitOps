from dotenv import load_dotenv
load_dotenv()

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.bungie.manifest import ManifestManager
from app.auth import router as auth_router
from app.api.loadout import router as loadout_router
from app.api.chat import router as chat_router
from app.api.capsule import router as capsule_router
from app.api.fireteam_advisor import router as fireteam_router
from app.api.vault import router as vault_router
from app.api.pathfinder import router as pathfinder_router
from app.api.stats import router as stats_router
from app.api.weekly import router as weekly_router
from app.api.recent import router as recent_router
from app.api.player_search import router as player_router
from app.api.catalog import router as catalog_router

manifest_manager = ManifestManager()


async def _ingest_lore_if_needed() -> None:
    """Run lore ingest in background if ChromaDB is empty. Fire-and-forget from lifespan."""
    if not os.getenv("OPENAI_API_KEY"):
        return
    try:
        import chromadb
        chroma = chromadb.PersistentClient(path=str(Path("data/chroma")))
        col = chroma.get_or_create_collection("destiny_lore")
        if col.count() > 0:
            print(f"[lore] ChromaDB ready: {col.count()} entries.")
            return
        print("[lore] ChromaDB empty — starting lore ingest (this takes ~5 min)...")
        proc = await asyncio.create_subprocess_exec(
            "python", "-m", "app.rag.ingest",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            print("[lore] Ingest complete.")
        else:
            print(f"[lore] Ingest failed:\n{stdout.decode()}")
    except Exception as e:
        print(f"[lore] Ingest check error: {e}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await manifest_manager.init_manifest()
    asyncio.create_task(_ingest_lore_if_needed())
    yield

app = FastAPI(title="OrbitOps Backend", lifespan=lifespan)

_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "https://localhost:5173,https://127.0.0.1:5173,http://localhost:8000",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _raw_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(loadout_router)
app.include_router(chat_router)
app.include_router(capsule_router)
app.include_router(fireteam_router)
app.include_router(vault_router)
app.include_router(pathfinder_router)
app.include_router(stats_router)
app.include_router(weekly_router)
app.include_router(recent_router)
app.include_router(player_router)
app.include_router(catalog_router)

@app.get("/health")
def health():
    return {"status": "ok"}

# Serve built React frontend — only present in the Docker image
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    _assets = STATIC_DIR / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str = ""):
        return FileResponse(str(STATIC_DIR / "index.html"))
