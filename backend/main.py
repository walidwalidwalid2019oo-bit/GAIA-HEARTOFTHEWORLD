"""HTTP API for GAIA's hosted intelligence engine."""
from __future__ import annotations

from uuid import uuid4
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from gaia.ai.engine import GaiaAI
from gaia.ai.provider import ProviderError

app = FastAPI(title="GAIA — Heart of the World", version="1.0.0")
ai = GaiaAI()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: str | None = Field(default=None, max_length=100)


@app.get("/health")
def health():
    return {"service": "GAIA", "status": "online", "ai": ai.status()}


@app.post("/chat")
def chat(request: ChatRequest):
    conversation_id = request.conversation_id or str(uuid4())
    try:
        return ai.respond(request.message.strip(), conversation_id)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
