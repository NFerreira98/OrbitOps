from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.bungie.manifest import ManifestManager
from app.auth import router as auth_router
from app.api.loadout import router as loadout_router
from app.api.chat import router as chat_router

manifest_manager = ManifestManager()

@asynccontextmanager
async def lifespan(_app: FastAPI):
    await manifest_manager.init_manifest()
    yield

app = FastAPI(title="OrbitOps Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:5173", "https://127.0.0.1:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(loadout_router)
app.include_router(chat_router)

@app.get("/")
def read_root():
    return {"status": "ok", "app": "OrbitOps"}
