# CampionAI — Product Requirements & Build Log

## Original Problem Statement
A privacy-first, multimodal AI daily companion that feels like a trusted close friend — remembers you (with permission), knows your life context, checks in proactively, and hands off to real humans when it matters. Web + Mobile (shared backend). Free for individuals. v1 = text-first web MVP, adults-only (18+), English.

## User Choices (locked)
- **Models:** OpenRouter-ready model router (admin can search/add any OpenRouter model). Running on the **Emergent universal LLM key** now; OpenRouter switchable in Admin > Provider Settings.
- **Auth:** Email + password (JWT). Google OAuth deferred.
- **Crisis hotlines:** Multi-country directory; user picks country at onboarding; IP-country auto-detect via Cloudflare `CF-IPCountry` header.
- **Check-ins:** Daily by default.
- **Scope:** Text chat + memory + safety + admin (web only). Voice/vision/mobile deferred.

## Architecture
- **Frontend:** React + Tailwind + Framer Motion. Earthy "Apple-glass" design system (Manrope/Figtree, sage + terracotta palette). Pages: Landing, Auth, Onboarding (4-step), Chat, Admin.
- **Backend:** FastAPI. Files: `server.py` (routes), `models.py`, `auth.py` (JWT+bcrypt), `llm_router.py` (Emergent + OpenRouter, cheap/medium/powerful tiers), `safety.py` (deterministic keyword + model verifier), `memory_engine.py` (decision engine), `hotlines.py` (country directory).
- **DB:** MongoDB collections: users, sessions, messages, memories, safety_events, professionals, model_config, provider_settings. UUID string ids.
- **Chat:** SSE streaming (`POST /api/chat/stream`): meta → delta* → done{escalation, memories_saved, risk}.

## User Personas
- Adults (18+) wanting everyday companionship: work, study, family, relationships, stress, wins, random thoughts.
- Admins: manage model routing, OpenRouter key, verified professionals, review safety events.

## Core Requirements (static)
- Warm, consistent, clearly-labeled AI companion; never diagnoses or clinically probes.
- Memory decision engine (DO_NOT_STORE / TEMPORARY / SESSION / LONG_TERM); user view/edit/forget; Private Mode (session-only).
- Safety: deterministic keyword net + powerful-model verifier → high-risk auto-escalation to trusted contact + verified professional + local crisis hotline; safety events audited.
- Onboarding captures name, 18+ confirm, country, one trusted contact, explicit safety consent, check-in frequency.
- Data export + delete-everything. Per-user isolation.

## Implemented (2026-06)
- [x] Email/password JWT auth, admin seed (admin@campionai.com / Admin@12345).
- [x] 4-step onboarding with age + safety consent gating (backend-enforced).
- [x] Warm streaming companion chat with personality + memory + recent-transcript context.
- [x] Model router (Emergent OpenAI/Anthropic + OpenRouter), admin-configurable tiers + OpenRouter model search.
- [x] Memory decision engine + Memory drawer (view/forget) + Private Mode toggle.
- [x] Safety classifier + hard escalation UI + audit; escalation copy reflects real delivery state.
- [x] Human handoff (consented summary) dialog.
- [x] Proactive daily check-in engine + banner (now personalized w/ recent moments).
- [x] Data export (JSON download) + delete-everything.
- [x] Admin panel: stats, model routing, provider/OpenRouter settings, professionals CRUD, safety-event review, Voice & alerts tab + integration status.
- [x] **REDESIGN → "Obsidian & Platinum"** dark premium theme (Cormorant Garamond serif, Outfit, JetBrains Mono; Signal Red reserved for safety; cardless chat, flushed inputs, sharp admin).
- [x] **Real Alerts**: Resend email + Twilio SMS to trusted contact & professional on escalation/handoff (graceful degradation; light up when keys added).
- [x] **Voice**: browser Web Speech STT (mic) + Fish Audio TTS playback (speaker toggle; admin-configurable; off until key added).
- [x] **CampionAI Plus (paid wellness)**: Stripe (emergentintegrations Flow B, test key) monthly ($9) + yearly ($86.40), app-managed 14-day free trial, one-time donations ($5/$15/$30). AI daily plan (meditation/yoga/breathing/tasks), natural-language food logging w/ AI macro estimate + totals, cal.com-style daily schedule, proactive coaching woven into chat. 402-gated behind active Plus.
- [x] Tested: iterations 1-4 (backend 75/75; frontend 100% of flows). Security: payment-status endpoint auth+ownership enforced.
- [x] **PayPal LIVE subscriptions**: live Client ID/Secret (verified), Product + Monthly($9)/Yearly($86.40) plans + webhook auto-created via API. New `/api/webhook/paypal` verifies PayPal signature and handles all 6 events (ACTIVATED→grant, PAYMENT.SALE.COMPLETED→extend, CANCELLED→mark, SUSPENDED/EXPIRED→revoke, PAYMENT.FAILED→past_due). Webhook points to https://nurekha.com/api/webhook/paypal. Backend tested (auth/error/signature paths).

## Implemented (2026-08) — Logout, PayPal-only billing, Doctor consultations
- [x] **Logout fixed**: `AccountMenu` mounted on every authenticated page (was Chat-only via SettingsDialog). Real server-side revocation — `users.token_version` is a JWT claim, `POST /api/auth/logout` increments it, killing every issued token including any leaked into a URL.
- [x] **Stripe removed entirely.** PayPal is the only rail. Real recurring subscriptions (auto-created billing plans, `PAYMENT.SALE.COMPLETED` renewals), signature-verified webhook as the authority, cancel/resume, billing history page. Prices now served from `GET /api/pricing` — one source of truth instead of three.
- [x] Payment grant made atomic (`find_one_and_update` claim) — the webhook and client poll could previously both grant, double-extending a subscription.
- [x] **Doctor consultations**: applications with automated KYC (Didit-default, provider-swappable) + manual licence review; country+language directory with ratings; scheduled bookings AND an instant "talk now" queue; doctor dashboard with availability, presence heartbeat, earnings.
- [x] **Live calls**: raw WebRTC, own WebSocket signaling, no vendor SFU. Perfect-negotiation offer/answer, self-hosted coturn with time-limited HMAC credentials. Video/audio/chat modes. Consult chat stored in `consult_messages`, never `messages` — the AI must never see clinical conversation.
- [x] **Free tier**: N volunteer sessions/month (admin-configurable) AND uncapped crisis sessions. The crisis flag is server-verified against a recent high-risk safety event, never taken from the client.
- [x] **Payouts**: doctors set their own rate, volunteers $0, admin-configurable commission, manual settlement ledger in Admin.
- [x] Crisis escalation now routes to real verified doctors and offers an immediate free consult. The fictional seeded "Dr. Maya Reyes" row was deleted.
- [x] Hardening carried along: upload path-traversal fix, streaming upload size cap, MongoDB indexes (there were none), 8-char minimum password.

### Known gaps (2026-08)
- Signaling keeps rooms in-process — single uvicorn worker only. Redis pub/sub needed to scale out.
- No session recording is possible with P2P WebRTC; needs an SFU if ever required.
- Consult refunds on cancellation are manual.
- `backend/tests/test_iteration4_plus_payments.py` still targets the deleted Stripe routes and needs rewriting for PayPal.
- **Unverified**: PayPal merchant accounts in Nepal have historically been unable to *receive* payments. Confirm before relying on the billing phase.

## Backlog
- **P1:** Provide production keys — Resend (email), Twilio (SMS), Fish Audio (voice), and a supported-country Stripe account to enable true recurring subscriptions (currently app-managed periods because Flow A sandbox is blocked for country NP).
- **P1:** True Stripe subscription mode + customer portal + auto-renew (replace app-managed periods) once a supported Stripe account is claimed.
- **P2 (Voice):** streaming ASR/TTS, barge-in, voice sessions sharing memory.
- **P2.5 Vision:** photo sharing + optional visual memory (object storage, encrypted).
- **P3 Teens / P4 B2B & self-hosted inference.**
- Housekeeping (optional): split server.py into payments/plus/wellness routers.

## Known Notes
- Trusted-contact/professional alerts + voice TTS require keys — until added they are surfaced in-app/logged (email/SMS) or disabled (voice).
- Stripe runs in TEST mode (card 4242 4242 4242 4242). Trial + access are app-managed; donations & payments are real test-mode checkouts.
- `GET /api/checkin` has a write side-effect — acceptable for MVP.

## Recovery + Improvements (2026-08-28)
- [x] **Env recovery**: both `.env` files were lost on restore (gitignored). Recreated `backend/.env` (new JWT_SECRET, MONGO_URL, DB_NAME=campionai, CORS, ADMIN_PASSWORD, EMERGENT_LLM_KEY) and `frontend/.env` (REACT_APP_BACKEND_URL + WDS_SOCKET_PORT). App fully restored. PayPal/Twilio/Resend/Fish/OpenRouter keys left empty (graceful degradation) — re-add to enable.
- [x] **Doctor UI/UX**: directory redesigned — avatars/initials, specialty chips, bio snippet, "per session" pricing, online count, **search bar** (`GET /api/doctors?q=`), skeleton loaders, richer empty state. Dashboard: doctor avatar in header, patient-initials avatars, mode labels, emerald "Waiting for you" queue with accented Accept. 5 demo verified doctors seeded via `seed_doctors.py`.
- [x] **AI Chat**: hover message actions (copy, regenerate last reply, thumbs up/down → `POST /api/chat/feedback`), tap-to-send starter prompts on empty state, floating scroll-to-bottom + smart auto-scroll, richer formatting (bullet lists + clickable links), sidebar "Talk to a doctor" link.
- [x] **Wellness planning/to-dos**: add-your-own to-do (`POST /api/wellness/plan/item`), delete (`DELETE .../item/{i}`), reorder up/down (`PUT .../plan/reorder`), **streak** badge + 100%-complete celebration (`GET /api/wellness/streak`), food meal tagging + grouped-by-meal logs (`meal` on `POST /api/wellness/food`), food edit (`PUT /api/wellness/food/{fid}`).
- [x] Backend: 27/27 new-endpoint tests passed (auth-gated, Plus-gated, validation 400/404/422). Frontend compiled successfully.

## 20-Feature Program (2026-08-28)
Phased build of 20 requested features. Phase 1 shipped:
- [x] **Phase 1 — Wellness pack** (5/20): Mood journal + 30-day trend graph (`POST /api/wellness/mood`, `GET /api/wellness/mood/trends`, upsert 1/day), Gratitude jar (`POST/GET/DELETE /api/wellness/gratitude`, `/random`), Guided breathing player (frontend `BreathingPlayer.js`, box-breathing animation), Daily mood check-in (5-emoji picker), Habit badges (`GET /api/wellness/badges`, 6 derived badges + progress). New Wellness tabs: Mood, Breathe, Gratitude + badges strip. Backend 15/15 tests passed. Frontend compiled.
- [x] **Phase 2 — Experience** (4/20): Light/warm theme toggle (`lib/theme.js` + `.light` CSS vars, toggle in Settings → Feel tab; app pages use CSS vars, marketing pages keep bespoke dark art). Personality/tone quiz (4 tones → `communication_style`, injected into `build_system_prompt` with concrete guidance). Keepsake export (enriched `GET /api/data/export` + printable HTML "keepsake" you can save as PDF + JSON download). Private chats — already existed (MemoryDrawer toggle + `private_mode` respected in chat), verified.
- [x] **Phase 3 — Chat** (3/20): Mood-aware replies (recent `mood_entries` injected into chat system prompt, non-private only). Pin-to-memory (`POST /api/memories/pin` → LONG_TERM memory; Pin button in chat message actions + "save recap to memory"). Conversation summaries (`POST /api/sessions/{id}/summary` LLM recap; "Recap" button in chat header → dialog). Frontend compiled.
- [ ] Phase 4 — Doctor: availability calendar, ratings & reviews, in-session notes, follow-ups
- [ ] Phase 4 — Doctor: availability calendar, ratings & reviews, in-session notes, follow-ups
- [ ] Phase 5 — Safety: crisis-mode redesign + local hotlines, trusted circle
- [ ] Phase 6 — NEEDS KEYS: voice (Fish Audio), smart reminders
