# CampionAI

A privacy-first AI companion with human doctor consultations. FastAPI + MongoDB backend,
React SPA frontend.

See [memory/PRD.md](memory/PRD.md) for the product spec and build log.

## Running locally

```bash
# backend
cd backend && pip install -r requirements.txt && uvicorn server:app --reload --port 8000

# frontend
cd frontend && yarn install && yarn start
```

`emergentintegrations` comes from Emergent's private package index, not PyPI.

## Configuration

Backend reads `backend/.env`. Only the first three are required — everything else
degrades gracefully, and the app tells you in Admin → Integrations what is missing.

### Required

| Variable | Purpose |
|---|---|
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | Database name |
| `JWT_SECRET` | Signing key for session tokens |

### LLM

| Variable | Purpose |
|---|---|
| `EMERGENT_LLM_KEY` | Emergent universal key (also used for object storage) |
| `OPENROUTER_API_KEY` | Optional — admin can switch providers at runtime instead |

### Payments — PayPal only

Stripe has been removed. Subscriptions are real PayPal recurring plans; the webhook
is the authority for granting access.

| Variable | Purpose |
|---|---|
| `PAYPAL_CLIENT_ID` / `PAYPAL_SECRET` | REST app credentials |
| `PAYPAL_MODE` | `sandbox` (default) or `live` |
| `PAYPAL_WEBHOOK_ID` | **Required for webhooks.** Without it every webhook is rejected — an unconfigured deploy must not be trickable into granting access |

Billing plans are created automatically at startup and cached in `provider_settings`.
Point the PayPal webhook at `POST /api/webhook/paypal` and subscribe to:
`BILLING.SUBSCRIPTION.ACTIVATED`, `.CANCELLED`, `.SUSPENDED`, `.EXPIRED`,
`.PAYMENT.FAILED`, and `PAYMENT.SALE.COMPLETED`.

### Doctor identity verification (KYC)

Confirms an applicant is the person on their ID. It does **not** verify a medical
licence — no provider does that globally, so licence review stays manual in Admin.

| Variable | Purpose |
|---|---|
| `KYC_API_KEY` | Provider key. Unset = applications wait for manual review |
| `KYC_PROVIDER` | Default `didit` |
| `KYC_BASE_URL` | Override to swap providers without code changes |
| `KYC_WORKFLOW_ID` | Provider workflow, if required |
| `KYC_WEBHOOK_SECRET` | HMAC secret for `POST /api/webhook/kyc` |

### Live calls (WebRTC)

Calls are peer-to-peer with our own signaling — no vendor SFU, and therefore no
server-side recording. STUN covers most users; the rest need a TURN relay.

| Variable | Purpose |
|---|---|
| `TURN_HOST` | e.g. `turn.example.com:3478` |
| `TURN_SECRET` | Shared secret for coturn `use-auth-secret` |

Credentials are minted per request as time-limited HMACs. Never ship static TURN
credentials — they get scraped and your relay becomes someone else's bandwidth.

Matching coturn config:

```
listening-port=3478
use-auth-secret
static-auth-secret=<TURN_SECRET>
realm=<TURN_HOST>
```

### Alerts and voice

| Variable | Purpose |
|---|---|
| `RESEND_API_KEY`, `SENDER_EMAIL` | Escalation and doctor emails |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` | SMS alerts |
| `FISH_AUDIO_API_KEY` | Text-to-speech |
| `ADMIN_PASSWORD` | Seeded admin password (defaults to `Admin@12345` — change it) |
| `CORS_ORIGINS` | Comma-separated. Defaults to `*` — set this in production |

## Tests

```bash
cd backend && python selfcheck.py
```

`selfcheck.py` covers upload path safety, TURN credential derivation, doctor presence,
public-payload redaction, consult access rules, and the invariant that consult chat
never reaches the AI's `messages` collection. No dependencies beyond the app's own.

`backend/tests/` is an integration suite that runs against a deployed instance and
needs `REACT_APP_BACKEND_URL`.

## Frontend

```bash
cd frontend && yarn build
```
