# GAIA Wake-Up Experience

## Two different health checks

GAIA exposes two distinct checks:

- `GET /health/live`: lightweight process liveness. It returns `alive` when the API process can answer, without requiring provider credentials.
- `GET /health`: application readiness. It reports `ready` only when the AI provider and backend access-token configuration are present; otherwise it reports `setup_required`.

The Render platform health check should use `/health/live`. The client should use `/health` to decide whether chat is ready. A process can be alive while the provider is not configured.

## Why a timer alone is misleading

Render Free web services spin down after 15 minutes without inbound traffic. The next request starts the service, which can take about a minute. The 15-minute value is a server-side inactivity rule, not a countdown that the browser can reliably observe. Other requests may also affect the idle window.

GAIA must not display a fabricated "server sleeps in 14:59" countdown.

## Intended user experience

When the user opens GAIA or sends a request:

1. The client requests `/health`.
2. If readiness responds `ready`, show **GAIA ONLINE** immediately.
3. If the process is starting, the request times out, or the service is temporarily unavailable, show **WAKING GAIA** and an elapsed wait indicator (for example, "Connecting… 18 seconds").
4. Retry health checks with bounded backoff rather than polling every second.
5. When readiness reports `ready`, stop the timer and continue the original action.
6. If readiness reports `setup_required`, show a setup message rather than spinning forever.
7. If the backend remains unavailable, show a retry action and a clear error. Never pretend the request completed.

## Timer behavior

- Measure elapsed time from the first connection attempt using a monotonic browser timer.
- Do not promise an exact remaining time.
- Stop and clear the timer on success, cancellation, or final failure.
- Do not keep the backend awake by sending artificial traffic.
- Do not resend user chat content automatically unless the client can prove the original request was not accepted; avoid duplicate messages.

## Accessibility and design

Use the existing Horizon-inspired GAIA visual direction: dark natural surfaces, restrained cyan/teal status glow, and clear readable text. Expose connection state with a live status region for screen readers. Respect reduced-motion preferences. The animation is decorative; status text must remain understandable without it.

## Implementation dependency

The current website is still a frontend demonstration and is not connected to the FastAPI backend. Implement this experience as part of the real frontend/backend integration, not as a disconnected decorative countdown.
