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
- [x] Safety classifier + hard escalation UI (EscalationCard: hotlines + trusted contact + professional) + audit.
- [x] Human handoff (consented summary) dialog.
- [x] Proactive daily check-in engine + banner.
- [x] Data export (JSON download) + delete-everything.
- [x] Admin panel: stats, model routing, provider/OpenRouter settings, professionals CRUD, safety-event review/resolve.
- [x] Tested: iteration_1 (backend 26/26, frontend core), iteration_2 (all fixes verified).

## Backlog
- **P1:** Real trusted-contact/professional notifications (email/SMS) — currently surfaced in-app + logged only. Wire OpenRouter key for production model routing.
- **P1 (v1.5):** Personal-state signals surfaced gently; richer memory editing; check-in scheduler as background job (make GET /api/checkin idempotent / move to POST).
- **P2 (v2 Voice):** streaming ASR/TTS, barge-in, voice sessions sharing memory.
- **P2.5 Vision:** photo sharing + optional visual memory (object storage, encrypted).
- **P3 Teens / P4 B2B & self-hosted inference.**

## Known Notes
- Trusted-contact alert + professional handoff are **surfaced in-app and audited only** — no real SMS/email is sent in v1 (by design).
- `GET /api/checkin` has a write side-effect (consumes check-in) — acceptable for MVP, move to background job later.
