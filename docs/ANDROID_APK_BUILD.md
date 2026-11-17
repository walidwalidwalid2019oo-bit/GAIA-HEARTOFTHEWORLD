# GAIA V11 Android APK build

The Android project wraps the existing mobile-first website in a native Android
WebView shell. The website files are packaged into the APK at build time; the
FastAPI backend is not bundled.

## Build

GitHub Actions runs `.github/workflows/android-apk.yml` on pushes to
`gaia-v11-android-apk`, matching pull requests, or manual dispatch.

The workflow builds a debug APK with Android Gradle Plugin 8.7.3, Gradle 8.9,
and Java 17. The artifact is named `GAIA-V11-Android-debug`.

## Important limits

- This is an installable debug APK, not a Play Store release.
- Account login, chat, and cloud memory require a separately deployed HTTPS
  backend and a backend CORS allowlist that includes
  `https://appassets.androidplatform.net`.
- The backend is not currently deployed, so online account features are not
  expected to work in this first packaged build.
- Google/GitHub OAuth, phone calls, SMS, push notifications, and native
  background services are not implemented.
- The APK contains no provider API key or backend secret.
- The WebView uses a secure app-assets origin, disables cleartext traffic,
  and opens ordinary external web links in the browser.

Do not use real passwords or personal data in this preview until the backend
is deployed and its authentication/security configuration has been reviewed.
