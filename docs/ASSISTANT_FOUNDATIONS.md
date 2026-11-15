# GAIA Personal Assistant Foundations

This milestone adopts selected architecture patterns from research into
open-source personal assistants. It is an independent GAIA implementation;
it does not copy another project's source files.

## Implemented in this milestone

### Explicit long-term memory

- Long-term facts are stored in a separate SQLite table from conversation turns.
- A fact is saved only through an explicit authenticated request.
- Facts can be listed by category and individually deleted.
- Credential-shaped text is rejected by a conservative pattern check.
- Deletion requires an explicit confirmation field.
- These endpoints use the existing shared backend bearer token. This is still
  a single-owner development arrangement, not per-user authentication.

Routes:

- `GET /memory/facts?category=projects&limit=100`
- `POST /memory/facts` with `{"category":"projects","content":"..."}`
- `DELETE /memory/facts/{fact_id}` with `{"confirm":true}`

Conversation history remains separate. Saving a chat turn does not silently
promote it into long-term memory.

### Action-risk and approval primitives

`gaia.assistant.policy` defines four risk levels:

| Level | Decision |
|---|---|
| `safe` | Execute |
| `monitor` | Execute and record for review |
| `ask` | Require explicit approval |
| `block` | Refuse; approval cannot override it |

The SQLite `ApprovalLedger` stores a short-lived approval against the exact
action name and canonicalized argument hash. An approval can be consumed once.
Changing the action or any argument invalidates the approval.

This is a foundation only: GAIA does not yet register external action handlers,
operate the phone, read email, manipulate files, or execute model-generated
commands. Do not describe an approval ticket as an executed action.

## Next architecture layers

1. A typed action registry with explicit capabilities and input schemas.
2. Read-only integrations first (for example, user-selected files or email
   summaries), with clear source and permission boundaries.
3. A bounded task planner with observable progress, cancellation, and a final
   evidence-based result.
4. Write integrations only after per-action risk rules and exact approval are
   connected to the executor.
5. Scheduled routines that cannot grant themselves new permissions.

## Security boundaries

- Provider keys stay on the backend, never in the website or Android client.
- No arbitrary shell, code execution, unrestricted file access, or unrestricted
  device control is part of this milestone.
- A shared bearer token embedded in a distributed mobile app is not secure
  production authentication. Per-user identity, rate limits, TLS, and abuse
  controls are required before public deployment.
- The credential-text filter is a guardrail, not a secret detector guarantee.
  Never submit passwords, API keys, recovery codes, or other credentials as
  memory facts.
