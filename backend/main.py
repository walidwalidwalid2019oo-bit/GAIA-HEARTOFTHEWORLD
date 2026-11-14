"""HTTP API for GAIA's hosted intelligence engine."""
from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from gaia.ai.engine import GaiaAI
from gaia.ai.provider import ProviderError

app = FastAPI(title="GAIA — Heart of the World", version="1.0.1")
ai = GaiaAI()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: str | None = Field(default=None, max_length=100)


@app.get("/health")
def health():
    provider = ai.status()
    ready = bool(provider.get("provider_configured"))
    return {
        "service": "GAIA",
        "status": "ready" if ready else "setup_required",
        "ai": provider,
    }


@app.post("/chat")
def chat(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be blank.")
    conversation_id = (request.conversation_id or "").strip() or str(uuid4())
    try:
        return ai.respond(message, conversation_id)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
