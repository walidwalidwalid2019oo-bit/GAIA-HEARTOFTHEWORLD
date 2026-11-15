# GAIA V19 Release Security Plan

## Release policy

GAIA is a private development project until version 19. No public Play Store release,
public APK distribution, or production launch is authorized before V19. Earlier
versions are development milestones only. This is a product release gate, not a
promise that V19 will automatically be safe to publish.

## Core finding: API provider keys cannot be hidden inside an APK

An Android package is controlled by its recipient. Static strings, resources,
native libraries, encrypted blobs, obfuscated code, and build-time injected values
can all be inspected or extracted by a determined person. Obfuscation and runtime
hardening may increase effort, but they do not turn a client-side provider key into
a server secret.

Never package Groq, OpenAI, Gemini, or other provider master keys in the GAIA app.
Never embed a shared GAIA backend bearer token in the APK either.

Android Keystore is useful for protecting user-specific cryptographic material or
refresh/session credentials stored on a device. It does not make a provider master
key safe to distribute to every app installation.

## Recommended request architecture

1. The Android app authenticates the user with a supported identity flow.
2. The backend issues short-lived, revocable, narrowly scoped session credentials.
3. The app calls GAIA over HTTPS using that session.
4. The backend validates identity, authorization, request size, quotas, rate limits,
   and (where justified) app/device integrity signals.
5. The backend selects an allowed provider and model using server-side policy.
6. The backend retrieves provider credentials from a managed secrets facility and
   calls the provider server-to-server.
7. The backend returns only the result and safe metadata needed by the app.

The mobile app must not be able to select arbitrary provider URLs, read server
environment variables, request raw provider keys, or bypass backend authorization.

## Backend authentication and abuse controls

- Replace the current single shared development bearer token for mobile use with
  per-user authentication and short-lived access sessions.
- Use refresh-token rotation/revocation and secure local storage where applicable.
- Scope sessions to the minimum capabilities required.
- Enforce authorization on every endpoint; client-side UI checks are not security.
- Add per-account and per-IP rate limits, concurrency limits, request-size limits,
  provider/model allowlists, daily usage budgets, and emergency kill switches.
- Add abuse detection and cost alerts. Do not rely on app package name, a static
  app API key, CORS, or an unverified device identifier as authentication.
- Do not log provider keys, session tokens, passwords, or full sensitive prompts.
  Redact authorization headers and sensitive fields.
- Keep authentication, provider access, and user-data authorization as separate
  backend responsibilities.

## Secrets management

- Use a managed secret store or the hosting platform's encrypted secret bindings.
- Keep development, staging, and production credentials separate.
- Grant the backend workload access only to the exact secrets it needs.
- Rotate provider keys and revoke compromised versions promptly.
- Audit secret access and keep secrets out of Git, build logs, crash reports,
  analytics, source maps, and client configuration.
- A Cloudflare Worker may serve as an API gateway/proxy if its secrets are stored
  using Cloudflare's Secret bindings. It must still validate user sessions,
  authorize each request, apply quotas, and avoid becoming an unrestricted proxy.
- The existing FastAPI backend can also perform the server-side provider call.
  The deployment choice should be made before implementing production auth.

## Android platform protections

- Use HTTPS for every remote request.
- Use Android Keystore for device-held cryptographic/session material where
  appropriate; do not use it to justify distributing provider secrets.
- Consider Google Play Integrity as an additional backend-verified risk signal
  for sensitive requests. The backend must verify the integrity token with
  Google's service and bind it to the request. Integrity is defense in depth,
  not a replacement for user authentication or authorization.
- Request only Android permissions required for a feature.
- Keep debug builds, test endpoints, verbose logs, and development credentials
  out of release artifacts.
- Sign release builds using a protected signing process and keep signing material
  out of source control.

## CI and release checks

Before any release candidate:
- Scan source, commit history, build artifacts, and dependencies for secrets.
- Verify no provider key or shared backend token exists in the APK/AAB.
- Verify the backend rejects missing, expired, revoked, malformed, and
  insufficiently scoped sessions.
- Verify rate limits, quotas, model allowlists, and abuse controls server-side.
- Test provider key rotation and emergency revocation.
- Verify no sensitive headers or values appear in logs.
- Review dependency vulnerabilities and Android permissions.
- Run API security tests and an independent review of high-risk flows.
- Complete Play Console declarations and privacy/data-safety work only when the
  actual app behavior and data handling are known.

## What is true in GAIA today

- The backend already keeps provider credentials in server-side configuration.
- The current API uses a single shared development bearer token. It is not
  production user authentication and must never be embedded in a distributed APK.
- The current long-term memory and action-approval additions are foundations, not
  a production-ready automation service.
- GAIA is not deployed, and no live provider request has been verified.

## Implementation order

1. Choose the eventual backend hosting model and identity provider.
2. Design per-user authentication, session lifecycle, authorization scopes, and
   account isolation.
3. Add rate limits, usage budgets, audit events, and provider allowlists.
4. Integrate a managed secret store and key rotation procedure.
5. Add optional Play Integrity verification for selected high-risk requests.
6. Build an Android client that contains no provider master key or shared backend
   secret.
7. Add automated APK/AAB secret scanning and release-candidate security tests.
8. Keep public release blocked until the V19 security and product checklist passes.

## Research references

- Android Developers: Security checklist
  https://developer.android.com/privacy-and-security/security-tips
- Android Developers: Insecure API usage
  https://developer.android.com/privacy-and-security/risks/insecure-api-usage
- OWASP MASWE-0004: Sensitive Data Hardcoded in the App Package
  https://mas.owasp.org/MASWE-0004/
- OWASP Mobile Application Security Cheat Sheet
  https://cheatsheetseries.owasp.org/cheatsheets/Mobile_Application_Security_Cheat_Sheet.html
- Android Developers: Play Integrity overview
  https://developer.android.com/google/play/integrity/overview
- Cloudflare Workers: Secrets
  https://developers.cloudflare.com/workers/configuration/secrets/
- Google Cloud: Secret Manager best practices
  https://docs.cloud.google.com/secret-manager/docs/best-practices
