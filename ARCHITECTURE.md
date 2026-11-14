# GAIA — Advanced Intelligence Architecture

## Goal

Build an AI platform with one central model-driven coordinator, six specialist perspectives, persistent conversation memory, and a permission-controlled tool layer.

## Current architecture

- **API layer:** FastAPI exposes health and chat endpoints.
- **Central engine:** \`gaia.ai.engine.GaiaAI\` composes the central GAIA instruction with one specialist instruction.
- **Specialists:** APOLLO, ARTEMIS, HEPHAESTUS, MINERVA, POSEIDON, and DEMETER are defined as distinct roles and routing hints.
- **Model adapter:** OpenAI-compatible Chat Completions API. Configure the endpoint and model through environment variables.
- **Memory:** SQLite conversation history, separated by conversation ID.
- **Credential handling:** the backend loads a private local \`.env\` for development or receives secrets from its deployment host. The Android/browser client must never contain provider credentials.

## Important current limitations

- This is one model call with a selected specialist prompt, not six independent models or autonomous agents.
- The provider adapter is implemented and tested with mocked responses, but no live provider request has been verified.
- No external tools are enabled yet. The model cannot execute code, browse, send messages, or control devices.
- Conversation history is stored locally in SQLite on the backend. It is not semantic/vector memory yet.
- The API has not been deployed. Authentication, rate limits, and abuse protection are required before public hosting.

## Run locally

Install dependencies:

\`\`\`bash
pip install -r requirements.txt
\`\`\`

Copy \`.env.example\` to \`.env\` and replace the placeholder values privately:

\`\`\`bash
cp .env.example .env
\`\`\`

Set \`GAIA_API_KEY\`, \`GAIA_MODEL\`, and optionally \`GAIA_BASE_URL\` in that private file. Remote provider URLs must use HTTPS; plain HTTP is accepted only for localhost development. \`python-dotenv\` loads \`.env\` for the backend process. Never commit \`.env\`, paste a key into source code, or place a provider key in the Android app.

Start the service:

\`\`\`bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
\`\`\`

Check \`GET /health\`, then send \`POST /chat\` with JSON containing \`message\` and optionally \`conversation_id\`. Health reports \`setup_required\` until a non-placeholder key and model plus a valid endpoint are configured.

## Next milestones

1. Verify one real provider request using a privately configured test key.
2. Add explicit memory controls: inspect, delete, and opt-in facts.
3. Add a typed tool registry with per-tool permissions and user confirmation for consequential actions.
4. Add a mobile-friendly client that talks only to the GAIA backend.
5. Add deployment configuration, authentication, rate limits, and abuse protection before public hosting.
