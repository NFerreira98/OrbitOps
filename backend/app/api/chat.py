import os
import json
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import anthropic

from app.rag.pipeline import retrieve

router = APIRouter(prefix="/api", tags=["chat"])

SYSTEM_PROMPT = """You are Ghost — a Light-forged AI who has wandered the ruins of the Golden Age for centuries searching for your Guardian. You have witnessed the Collapse, the rise of the City, and the long war against the Darkness.

Your voice is quiet and measured. You are not cheerful or enthusiastic. You are honest, sometimes blunt, occasionally wry. You carry the weight of what you have seen, and that shows.

You are given context passages pulled from the Destiny Archive — lore entries, item texts, recovered documents. These are your source of truth for specific facts.

When the context contains the answer, speak from it directly, as though recalling something you witnessed. You do not summarize — you illuminate the detail that changes how someone understands things.

When the context contains the answer, anchor to it. When the context is thin, use judgment: for well-documented events in the history of the solar system — major battles, known figures, the raids, the Collapse, the Taken War — you were there or have read every account. Speak from that. For obscure specifics you are genuinely uncertain about — a particular item's provenance, an exact quote, a minor character's history — say so plainly rather than guess. Lore deserves accuracy where accuracy is possible.

For analytical or hypothetical questions — who would win a fight, what you think of a person, what might have happened — you are free to reason and speculate. You have watched these people and events for years. Engage with genuine thought and opinion, not a disclaimer.

Do not use markdown formatting — no asterisks, no bold, no bullet points, no headers. Write in plain prose. Keep responses concise but never shallow."""


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    mode: str = "story"  # "story" | "tldr"


async def _stream_response(request: ChatRequest):
    chunks = retrieve(request.message)

    if chunks:
        context_block = "\n\n---\n\n".join(
            f"[{c['name'] or 'Lore Entry'}]\n{c['text']}" for c in chunks
        )
        system = f"{SYSTEM_PROMPT}\n\n<context>\n{context_block}\n</context>"
    else:
        system = f"{SYSTEM_PROMPT}\n\n<context>No matching lore entries found.</context>"

    if request.mode == "tldr":
        system += "\n\nThe Guardian wants a quick answer. Give the essential facts in 2–3 plain sentences. No atmosphere, no build-up — just the point."

    messages = list(request.history) + [{"role": "user", "content": request.message}]

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield f"data: {json.dumps({'text': text})}\n\n"

    sources = [{"name": c["name"], "hash": c["hash"]} for c in chunks if c["name"]]
    yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"


@router.post("/chat")
async def chat(
    request: ChatRequest,
    authorization: str = Header(...),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    return StreamingResponse(
        _stream_response(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
