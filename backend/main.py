"""HTTP API for GAIA's hosted intelligence engine."""
from __future__ import annotations

import hmac
import os
import re
from uuid import uuid4
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

load_dotenv(override=False)

from gaia.ai.engine import GaiaAI
from gaia.ai.provider import ProviderError
from gaia.assistant.auth import AuthenticationError, UserAuth
from gaia.assistant.memory import LongTermMemory, MemoryFactError
from gaia.storage import database_backend

app = FastAPI(title="GAIA — Heart of the World", version="1.5.0")
_allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("GAIA_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if _allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

ai = GaiaAI()
user_auth = UserAuth(engine=ai.memory.engine)
long_term_memory = LongTermMemory(engine=ai.memory.engine)
_CONVERSATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}")


def _bearer_token(authorization: str | None) -> str | None:
    scheme, separator, token = (authorization or "").partition(" ")
    if not separator or scheme.casefold() != "bearer" or not token.strip():
        return None
    return token.strip()


def _require_user_session(authorization: str | None) -> str:
    token = _bearer_token(authorization)
    owner_id = user_auth.resolve_session(token or "")
    if owner_id is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return owner_id


def _require_api_access(authorization: str | None) -> str:
    """Resolve a real account session; allow the legacy token only in dev mode."""
    token = _bearer_token(authorization)
    owner_id = user_auth.resolve_session(token or "")
    if owner_id:
        return owner_id

    shared_enabled = os.getenv("GAIA_ALLOW_SHARED_TOKEN", "false").casefold() == "true"
    api_token = os.getenv("GAIA_API_TOKEN", "").strip()
    if shared_enabled and len(api_token) >= 32 and not api_token.casefold().startswith(("put_", "your_", "replace_")):
        if token and hmac.compare_digest(token, api_token):
            return "shared-token-owner"
    raise HTTPException(status_code=401, detail="Missing or invalid account session.")


def _validate_conversation_id(conversation_id: str) -> str:
    if not _CONVERSATION_ID.fullmatch(conversation_id):
        raise HTTPException(status_code=422, detail="Conversation ID contains unsupported characters.")
    return conversation_id


class AccountRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    model_config = ConfigDict(extra="forbid")


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
    return {"service": "GAIA", "status": "alive"}


@app.get("/health")
def health():
    provider = ai.status()
    return {
        "service": "GAIA",
        "status": "ready" if provider.get("provider_configured") else "setup_required",
        "account_auth": "enabled",
        "shared_token_auth": os.getenv("GAIA_ALLOW_SHARED_TOKEN", "false").casefold() == "true",
        "ai": provider,
        "database_backend": database_backend(ai.memory.engine),
        "long_term_memory": "explicit_owner_scoped_facts",
    }


@app.post("/auth/register")
def register(request: AccountRequest):
    try:
        account = user_auth.create_user(request.email, request.password)
        session = user_auth.issue_session(account["user_id"])
    except AuthenticationError as exc:
        # Do not reveal whether an email is already registered.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"account": account, "session": session}


@app.post("/auth/login")
def login(request: AccountRequest):
    account = user_auth.verify_credentials(request.email, request.password)
    if account is None:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    try:
        session = user_auth.issue_session(account["user_id"])
    except AuthenticationError as exc:
        raise HTTPException(status_code=400, detail="Could not create a session.") from exc
    return {"account": account, "session": session}


@app.get("/auth/me")
def current_account(authorization: str | None = Header(default=None)):
    owner_id = _require_user_session(authorization)
    # Email is returned only for the account represented by this valid session.
    with user_auth.engine.connect() as db:
        from sqlalchemy import text
        row = db.execute(text("SELECT user_id, email, created_at FROM users WHERE user_id=:id"),
                         {"id": owner_id}).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=401, detail="Account session is no longer valid.")
    return {"account": dict(row)}


@app.post("/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    token = _bearer_token(authorization)
    owner_id = user_auth.resolve_session(token or "")
    if owner_id is None or not user_auth.revoke_session(token or ""):
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return {"logged_out": True}


@app.post("/chat")
def chat(request: ChatRequest, authorization: str | None = Header(default=None)):
    owner_id = _require_api_access(authorization)
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be blank.")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in message):
        raise HTTPException(status_code=422, detail="Message contains unsupported control characters.")
    conversation_id = (request.conversation_id or "").strip()
    if conversation_id:
        _validate_conversation_id(conversation_id)
    conversation_id = conversation_id or str(uuid4())
    try:
        return ai.respond(message, conversation_id, request.specialist, owner_id=owner_id)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/conversations")
def list_conversations(
    authorization: str | None = Header(default=None),
    limit: int = Query(default=50, ge=1, le=100),
):
    owner_id = _require_api_access(authorization)
    return {"conversations": ai.memory.conversations(limit=limit, owner_id=owner_id)}


@app.get("/conversations/{conversation_id}")
def read_conversation(conversation_id: str, authorization: str | None = Header(default=None)):
    owner_id = _require_api_access(authorization)
    conversation_id = _validate_conversation_id(conversation_id)
    messages = ai.memory.get_conversation(conversation_id, owner_id=owner_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"conversation_id": conversation_id, "messages": messages}


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, authorization: str | None = Header(default=None)):
    owner_id = _require_api_access(authorization)
    conversation_id = _validate_conversation_id(conversation_id)
    if not ai.memory.delete_conversation(conversation_id, owner_id=owner_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"deleted": True, "conversation_id": conversation_id}


@app.get("/memory/facts")
def list_memory_facts(
    authorization: str | None = Header(default=None),
    category: str | None = Query(default=None, max_length=40, pattern=r"^[a-z][a-z0-9_-]{0,39}$"),
    limit: int = Query(default=100, ge=1, le=200),
):
    owner_id = _require_api_access(authorization)
    return {"facts": long_term_memory.list(category=category, limit=limit, owner_id=owner_id)}


@app.post("/memory/facts")
def create_memory_fact(request: MemoryFactCreateRequest, authorization: str | None = Header(default=None)):
    owner_id = _require_api_access(authorization)
    try:
        fact = long_term_memory.add(request.category, request.content, owner_id=owner_id)
    except MemoryFactError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"saved": True, "fact": fact}


@app.delete("/memory/facts/{fact_id}")
def delete_memory_fact(
    fact_id: str,
    request: MemoryFactDeleteRequest,
    authorization: str | None = Header(default=None),
):
    owner_id = _require_api_access(authorization)
    if request.confirm is not True:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required.")
    if not long_term_memory.delete(fact_id, owner_id=owner_id):
        raise HTTPException(status_code=404, detail="Memory fact not found.")
    return {"deleted": True, "fact_id": fact_id}
