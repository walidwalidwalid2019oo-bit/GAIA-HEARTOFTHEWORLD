"""HTTP API for GAIA's hosted intelligence engine."""
from __future__ import annotations

import hmac
import os
import re
from uuid import uuid4
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

# Load a private local .env before the provider reads its configuration.
# Production deployments should inject secrets through their host's secret manager.
load_dotenv(override=False)

from gaia.ai.engine import GaiaAI
from gaia.ai.provider import ProviderError
from gaia.assistant.memory import LongTermMemory, MemoryFactError

app = FastAPI(title="GAIA — Heart of the World", version="1.3.0")
ai = GaiaAI()
long_term_memory = LongTermMemory()
_CONVERSATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}")


def _configured_api_token() -> str | None:
    """Return a usable backend access token; reject example placeholders."""
    token = os.getenv("GAIA_API_TOKEN", "").strip()
    if len(token) < 32 or token.casefold().startswith(("put_", "your_", "replace_")):
        return None
    return token


def _require_api_access(authorization: str | None) -> None:
    """Protect private chat and memory endpoints with the backend access token."""
    api_token = _configured_api_token()
    if api_token is None:
        raise HTTPException(
            status_code=503,
            detail="GAIA_API_TOKEN is not configured on the backend.",
        )

    scheme, separator, supplied_token = (authorization or "").partition(" ")
    if (
        not separator
        or scheme.casefold() != "bearer"
        or not hmac.compare_digest(supplied_token, api_token)
    ):
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token.")


def _validate_conversation_id(conversation_id: str) -> str:
    if not _CONVERSATION_ID.fullmatch(conversation_id):
        raise HTTPException(status_code=422, detail="Conversation ID contains unsupported characters.")
    return conversation_id


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: str | None = Field(default=None, max_length=100)
    specialist: Literal["GAIA", "APOLLO", "ARTEMIS", "HEPHAESTUS", "MINERVA", "POSEIDON", "DEMETER", "AETHER", "ELEUTHIA", "HADES"] | None = None

    model_config = ConfigDict(extra="forbid")


class MemoryFactCreateRequest(BaseModel):
    category: str = Field(default="general", min_length=1, max_length=40, pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    content: str = Field(min_length=1, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class MemoryFactDeleteRequest(BaseModel):
    confirm: bool

    model_config = ConfigDict(extra="forbid")


@app.get("/health/live")
def liveness():
    """Cheap process-liveness check; deliberately independent of AI credentials."""
    return {"service": "GAIA", "status": "alive"}


@app.get("/health")
def health():
    """Readiness check for the API, provider configuration, and access control."""
    provider = ai.status()
    auth_configured = _configured_api_token() is not None
    ready = bool(provider.get("provider_configured")) and auth_configured
    return {
        "service": "GAIA",
        "status": "ready" if ready else "setup_required",
        "api_auth_configured": auth_configured,
        "ai": provider,
        "long_term_memory": "sqlite_explicit_facts",
    }


@app.post("/chat")
def chat(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
):
    _require_api_access(authorization)

    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be blank.")
    if any(ord(char) < 32 and char not in "\\n\\r\\t" for char in message):
        raise HTTPException(status_code=422, detail="Message contains unsupported control characters.")

    conversation_id = (request.conversation_id or "").strip()
    if conversation_id:
        _validate_conversation_id(conversation_id)
    conversation_id = conversation_id or str(uuid4())

    try:
        return ai.respond(message, conversation_id, request.specialist)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/conversations")
def list_conversations(
    authorization: str | None = Header(default=None),
    limit: int = Query(default=50, ge=1, le=100),
):
    """List recent conversation summaries for the authenticated owner."""
    _require_api_access(authorization)
    return {"conversations": ai.memory.conversations(limit=limit)}


@app.get("/conversations/{conversation_id}")
def read_conversation(
    conversation_id: str,
    authorization: str | None = Header(default=None),
):
    """Read one conversation so the owner can inspect what GAIA retained."""
    _require_api_access(authorization)
    conversation_id = _validate_conversation_id(conversation_id)
    messages = ai.memory.get_conversation(conversation_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"conversation_id": conversation_id, "messages": messages}


@app.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    authorization: str | None = Header(default=None),
):
    """Delete one conversation from GAIA's SQLite history."""
    _require_api_access(authorization)
    conversation_id = _validate_conversation_id(conversation_id)
    if not ai.memory.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"deleted": True, "conversation_id": conversation_id}


@app.get("/memory/facts")
def list_memory_facts(
    authorization: str | None = Header(default=None),
    category: str | None = Query(default=None, max_length=40, pattern=r"^[a-z][a-z0-9_-]{0,39}$"),
    limit: int = Query(default=100, ge=1, le=200),
):
    """List deliberately saved long-term facts, separate from chat transcripts."""
    _require_api_access(authorization)
    return {"facts": long_term_memory.list(category=category, limit=limit)}


@app.post("/memory/facts")
def create_memory_fact(
    request: MemoryFactCreateRequest,
    authorization: str | None = Header(default=None),
):
    """Save a fact only after an explicit authenticated request."""
    _require_api_access(authorization)
    try:
        fact = long_term_memory.add(request.category, request.content)
    except MemoryFactError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"saved": True, "fact": fact}


@app.delete("/memory/facts/{fact_id}")
def delete_memory_fact(
    fact_id: str,
    request: MemoryFactDeleteRequest,
    authorization: str | None = Header(default=None),
):
    """Delete one long-term fact only when the client explicitly confirms."""
    _require_api_access(authorization)
    if request.confirm is not True:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required.")
    if not long_term_memory.delete(fact_id):
        raise HTTPException(status_code=404, detail="Memory fact not found.")
    return {"deleted": True, "fact_id": fact_id}
