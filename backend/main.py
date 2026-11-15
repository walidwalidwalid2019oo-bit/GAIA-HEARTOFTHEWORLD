"""HTTP API for GAIA's hosted intelligence engine."""
from __future__ import annotations

import hmac
import os
import re
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

# Load a private local .env before the provider reads its configuration.
# Production deployments should inject secrets through their host's secret manager.
load_dotenv(override=False)

from gaia.ai.engine import GaiaAI
from gaia.ai.provider import ProviderError

app = FastAPI(title="GAIA — Heart of the World", version="1.1.0")
ai = GaiaAI()
_CONVERSATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}")


def _configured_api_token() -> str | None:
    """Return a usable backend access token; reject example placeholders."""
    token = os.getenv("GAIA_API_TOKEN", "").strip()
    if len(token) < 32 or token.casefold().startswith(("put_", "your_", "replace_")):
        return None
    return token


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")


@app.get("/health")
def health():
    provider = ai.status()
    auth_configured = _configured_api_token() is not None
    ready = bool(provider.get("provider_configured")) and auth_configured
    return {
        "service": "GAIA",
        "status": "ready" if ready else "setup_required",
        "api_auth_configured": auth_configured,
        "ai": provider,
    }


@app.post("/chat")
def chat(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
):
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

    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be blank.")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in message):
        raise HTTPException(status_code=422, detail="Message contains unsupported control characters.")

    conversation_id = (request.conversation_id or "").strip()
    if conversation_id and not _CONVERSATION_ID.fullmatch(conversation_id):
        raise HTTPException(status_code=422, detail="Conversation ID contains unsupported characters.")
    conversation_id = conversation_id or str(uuid4())

    try:
        return ai.respond(message, conversation_id)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
