# BOBB AI Kiosk — Operational Failure-Mode Review

Date: 2026-06-12 · Scope: backend (`backend/app/`) + frontend (`frontend/src/`) as committed

## Executive Summary

The platform persists designs, variants, and recommendations durably in PostgreSQL and has a well-built `session_resumed` snapshot on WebSocket connect (`backend/app/api/ws.py`), but the pieces are not wired together into a recoverable kiosk: the **session ID lives only in an in-memory Zustand store** (no `localStorage` anywhere in `frontend/src`), so a browser refresh silently abandons the customer's journey even though all their data is sitting in the database. The **AI pipeline is orchestrated from the browser** (sequential HTTP calls in `ListeningScreen.tsx` — `backend/app/agents/orchestrator.py` referenced in CLAUDE.md does not exist), so any client-side interruption mid-pipeline strands the journey. Idle-timeout reset (`App.tsx` + `store/session.ts`) **reuses the previous customer's session ID**, creating real cross-customer data contamination. Redis is configured but entirely unused, and partial fal.ai failures are persisted but surfaced to the customer as blank tiles with no retry path. Overall operational posture: **fragile for a 40–60 customers/day van deployment** — two Critical and two High findings below.

---

## Scenario 1 — Browser refresh mid-journey (customer on PreviewScreen)

**What actually happens.** The Zustand store (`frontend/src/store/session.ts`) is created with `create()` and no `persist` middleware; `grep` confirms zero `localStorage`/`sessionStorage` usage in `frontend/src`. On refresh, `sessionId` is `null`, so the `useEffect` in `App.tsx` (~line 84) calls `api.createSession()` and the backend mints a **brand-new session** (`session_manager.create_session`). The WebSocket connects to the *new* session ID; in `ws.py` `is_reconnect` is `false` (the new ID was never in `active_sessions`), and the snapshot is a fresh `greeting` state. The elaborate recovery path — `is_reconnect` + `_infer_state()` in `ws.py` and `setPendingReconnect`/`SessionResumeOverlay` in `useWebSocket.ts` — is only reachable for a WS drop *without* a page reload (e.g. network blip), never for a refresh.

**Customer impact.** Kiosk lands on GreetingScreen. The customer's 4 generated designs vanish; they must retell their story and wait through the full ~2-minute generation again. On a 10–14-min journey budget this likely loses the sale.

**Data integrity.** Nothing is lost from the database — design, variants, and cached PNGs (`/cache/designs/{old_session_id}/`) all survive. They are simply unreachable from the UI because the old session ID is forgotten. The old session row is never marked `abandoned`.

**Staff recovery.** None possible from the kiosk UI. A staff member with DB access could find the design via `SELECT ... FROM sessions ORDER BY created_at DESC`, but there is no admin UI (out of MVP scope), so in practice the customer starts over.

**Severity: Critical** — refreshes on Android tablets (OS memory reclaim, mis-taps) are routine, and the failure defeats the entire recovery system that was built for it.

**Fix.** Persist `sessionId` with Zustand's `persist` middleware (`localStorage`, key e.g. `bobb_session_id`) in `store/session.ts`. In `App.tsx`, on boot call `GET /api/v1/sessions/{id}` (already exists in `backend/app/api/sessions.py`) — if found and not completed/abandoned, reuse it and let the existing `session_resumed` snapshot rebuild the screen; otherwise create a new session. Also change `ws.py` to treat `is_reconnect` as "session has prior progress" (derive from DB state, e.g. `latest_design is not None`) rather than presence in the in-process `active_sessions` dict, which is wiped on backend restart too.

---

## Scenario 2 — Redis restart mid-pipeline

**What actually happens.** Nothing. `redis_url` is declared in `backend/app/core/config.py:16` and `.env.example`, but a repo-wide grep shows **no code imports or connects to Redis**. Sessions are PostgreSQL-backed (`session_manager.py`); WebSocket registry is the in-process `active_sessions` dict in `ws.py`.

**Customer impact.** None. **Data integrity.** None. **Staff recovery.** None needed.

**Severity: Low** — but the configuration is a trap: ops staff will assume Redis matters (CLAUDE.md says "optional, for session caching") and may waste incident time on it, or future code may silently start depending on it.

**Fix.** Either remove `redis_url` from `config.py` and `.env.example` until used, or add a startup log in `main.py`'s `lifespan` stating Redis is configured but unused. Document in CLAUDE.md that session state is PostgreSQL-only.

---

## Scenario 3 — PostgreSQL restart while customer is on GeneratingScreen

**What actually happens.** The frontend's single long-lived call `api.generateImages()` maps to `POST /sessions/{id}/generate` (`backend/app/api/generate.py`). The handler reads the design, then awaits `svc.generate_variants()` for up to ~2 minutes **holding an open DB session from `Depends(get_db)`**. If PostgreSQL restarts during generation: (a) the images may still complete and be written to `/cache/designs/{sid}/`, but (b) `persist_variants(db, ...)` fails on the dead connection → unhandled exception → HTTP 500. `ListeningScreen.tsx`'s `catch` sets `pipelineError` and drops the customer back to LISTENING. Concurrently, the WebSocket reconnect loop in `useWebSocket.ts` reconnects; `_load_session_snapshot` in `ws.py` raises on its DB query (no try/except around the `db.execute` calls), which kills the WS coroutine — the frontend just reconnects with backoff until the DB pool recovers (asyncpg/SQLAlchemy will re-establish connections on new requests).

**Customer impact.** After watching the generating animation for up to two minutes, they see "Something went wrong. Please try again." on the story screen and must resubmit — re-running Claude story extraction, design strategy, and 4 fal.ai generations (real money and ~2 more minutes).

**Data integrity.** Variant DB rows are lost (transaction never committed). PNGs may be orphaned on disk in the cache directory. The design row + strategy JSON from the earlier `/design` call survive, so a retry of `/generate` alone would work — but the UI has no path that retries only generation.

**Staff recovery.** Restart-and-retry: ask the customer to press "Create My Design" again. If the backend pool wedges, staff must restart uvicorn.

**Severity: Medium** — recoverable with customer effort; DB restarts mid-window should be rare, but the blast radius is a full pipeline re-run.

**Fix.** In `generate.py`, release/reacquire the DB session around the long `generate_variants` await (or fetch strategy, close the session, generate, then open a fresh session for `persist_variants` with one retry on `OperationalError`). Wrap `_load_session_snapshot` in `ws.py` in try/except returning `_greeting_snapshot()` (or an explicit `error` frame) so a DB outage doesn't crash WS handlers. Add a "Retry generation" action on the error path that re-calls `/generate` with the existing `design_id` instead of restarting from story submission.

---

## Scenario 4 — fal.ai timeout / 5xx during generateImages

**What actually happens.** `FalAIProvider.generate` (`backend/app/services/image_gen.py`): a submit 5xx returns `GenerationResult(success=False, error="fal.ai submit failed: HTTP 5xx")` immediately; a hang is bounded by httpx timeouts (30s submit, 10s per status poll) and the 120s poll deadline (`_TIMEOUT_S`), after which `success=False, error="fal.ai generation timed out or failed"`. `ImageGenerationService.generate_variants` also catches raised exceptions per variant. `generate.py` then persists all 4 rows — failures stored as `is_fallback=True` with `image_url=None` (`design_service.py:85`) — broadcasts `variant_ready` with `success: false`, and returns HTTP **200** with the failed variants in the list. Frontend: `ListeningScreen.tsx` maps all variants (including `image_url: null`) into the store and transitions to PREVIEW. `useWebSocket.ts`'s `variant_ready` handler ignores the `success` flag entirely. Note worst case: 4 concurrent variants each up to ~120s+60s download; **no fetch timeout exists in `frontend/src/services/api.ts`**, so the browser waits the full duration on GeneratingScreen with no server-side progress (and `GENERATING` is excluded from `IDLE_TIMEOUT_ACTIVE_STATES` in `App.tsx`, so at least the kiosk won't reset under them).

**Customer impact.** If all 4 fail, the customer lands on a PreviewScreen of 4 blank/broken tiles with no error message — the HTTP call "succeeded". They can even select a broken variant.

**Data integrity.** Nothing lost; failures are correctly recorded with `error` strings, `provider_request_id`, and timing in `design_variants`. Good observability, bad UX.

**Staff recovery.** Staff must walk the customer back and resubmit the story (full pipeline re-run); no per-variant retry endpoint exists.

**Severity: High** — fal.ai instability is the most probable third-party failure for a van on mobile networks, and the system converts it into a silent broken preview.

**Fix.** (1) In `generate.py`, if `sum(v.success) == 0`, return a 502-style error (or `success: false` envelope) instead of 200, so `ListeningScreen.tsx`'s catch path shows the error. (2) In the frontend, filter `image_url === null` variants out of the preview grid and show "couldn't create this one" tiles. (3) Add `POST /sessions/{id}/generate` support for regenerating only failed variant numbers (the strategy JSON and seeds are already persisted). (4) Add one automatic retry in `FalAIProvider` on submit 5xx.

---

## Scenario 5 — Customer walks away mid-checkout; new customer 20 min later

**What actually happens.** CHECKOUT is in `IDLE_TIMEOUT_ACTIVE_STATES` (`App.tsx`), so after 3 minutes of no touches `useIdleTimeout` fires `handleIdleTimeout` → `reset()` + `setState(IDLE)`. Critically, `reset()` in `store/session.ts` **explicitly preserves `sessionId`** (`sessionId: get().sessionId`). The backend is never told anything: no abandon call, no state transition (in fact, grep shows **no API endpoint ever calls `session_manager.transition_state`** — the whole server-side state machine is dead code; `sessions.current_state` stays `greeting` forever). When the new customer taps IdleScreen 20 minutes later, `IdleScreen.tsx` does `setState(GREETING)` and the journey proceeds **on the previous customer's session ID**. Their story, design, and any order pile onto the same `sessions` row; the WS `session_resumed` on any reconnect would run `_infer_state` and offer the *previous* customer's `product_selection`/`preview` state to the *new* customer via the `SessionResumeOverlay`.

**Customer impact.** New customer mostly proceeds normally, but may be shown the prior customer's designs/recommendations on any WS reconnect — a privacy leak of a personal story rendered as artwork, and confusing UX.

**Data integrity.** Worse than loss: **contamination**. Two customers' journeys share one session row; analytics (`duration_seconds`, `completed`), pipeline correlation, and any future order linkage are corrupted. The abandoned checkout is never flagged `abandoned=true`, so the daily funnel metrics are wrong too.

**Staff recovery.** Invisible at the kiosk — staff won't notice. Untangling requires manual DB surgery on `designs.session_id`.

**Severity: Critical** — guaranteed to occur multiple times per day at 40–60 customers/day with walk-aways.

**Fix.** In `App.tsx`'s `handleIdleTimeout`: (1) call a new `POST /api/v1/sessions/{id}/abandon` endpoint (set `abandoned=true`, `current_state='idle'` via `session_manager`), (2) clear `sessionId` in `reset()` (remove the `sessionId: get().sessionId` carry-over) so the existing create-session effect mints a fresh session for the next customer. Same teardown should run when SuccessScreen returns to IDLE. Separately, wire the API handlers (story/design/generate) to actually call `transition_state` so `sessions.current_state` reflects reality — `_infer_state` in `ws.py` currently exists only because the DB state is never updated.

---

## Scenario 6 — Partial success: 2 of 4 variants generated

**What actually happens.** `generate_variants` uses `asyncio.gather` with per-variant try/except, so 2 successes and 2 failures all return. All 4 rows are persisted (`persist_variants`, failed ones `is_fallback=True`, `image_url=None`). The HTTP response is 200 with a mixed list; `ws_broadcast.send_variant_ready` fires 4 times (2 with `success: false`). `ListeningScreen.tsx` puts all 4 into `latestDesign.variants` regardless of success; `useWebSocket.ts`'s `variant_ready` handler also adds them without checking `m.success` (it doesn't even read the field). PreviewScreen renders a 2×2 grid with 2 images and 2 empty tiles; the customer can tap and `POST /designs/{id}/select` a fallback variant — `designs.py` only checks the variant belongs to the design, not `is_fallback`, so a **null-image variant can be locked for production**.

**Customer impact.** Confusing half-broken grid with no explanation. Worst case: customer selects a blank tile and the order proceeds toward production with no printable image.

**Data integrity.** None lost — errors, request IDs, seeds all stored. The gap is enforcement and presentation, not persistence.

**Staff recovery.** No regenerate path; staff must restart the customer's journey from story input. If a fallback variant was selected, staff would only discover it at the (manual) print queue.

**Severity: High** — partial failures are the *common* mode of API flakiness, and the select-a-fallback hole turns a UX bug into a fulfillment failure.

**Fix.** (1) In `designs.py` `select_design_variant`, reject variants where `variant.is_fallback` (409 with `suggested_action: "regenerate"`). (2) Add per-variant regeneration: accept `variant_numbers: list[int]` on `POST /sessions/{id}/generate` and only re-run/upsert those rows (strategy + seeds already in `designs.design_strategy_json`). (3) PreviewScreen: render failed tiles as a "Regenerate" button wired to (2). (4) Honor the `success` field in `useWebSocket.ts`'s `variant_ready` handler.

---

## Consolidated Fix Priority

| # | Scenario | Severity | Fix summary | Effort |
|---|----------|----------|-------------|--------|
| 5 | Walk-away → session reuse | Critical | Clear `sessionId` on idle reset; add `/sessions/{id}/abandon`; wire `transition_state` into API handlers | Low–Med |
| 1 | Browser refresh loses session | Critical | Persist `sessionId` via Zustand `persist`; rehydrate via existing `GET /sessions/{id}` + `session_resumed` snapshot; fix `is_reconnect` derivation | Low |
| 6 | Partial variant success | High | Block selecting `is_fallback` variants; per-variant regenerate endpoint; UI failed-tile treatment | Med |
| 4 | fal.ai timeout/5xx | High | Non-200 on total failure; surface errors in UI; submit retry; frontend fetch timeout | Med |
| 3 | PostgreSQL restart mid-gen | Medium | Don't hold DB session across generation; retry `persist_variants`; harden `_load_session_snapshot`; "retry generation" path | Med |
| 2 | Redis restart | Low | Remove or clearly mark unused `redis_url` config | Low |

### Cross-cutting notes

- `backend/app/agents/orchestrator.py` does not exist despite CLAUDE.md; the pipeline is browser-orchestrated (`ListeningScreen.tsx` / `ClarifyingScreen.tsx`). Moving orchestration server-side (single `POST /pipeline` driving WS progress events, which the broadcast plumbing already supports) would resolve much of Scenarios 1, 3, and 4 at once.
- The server-side state machine (`session_manager.STATE_TRANSITIONS`) is currently unreferenced by any endpoint; all screen transitions are client-local. Until that is wired up, `sessions.current_state` analytics and `_infer_state` fallback behavior cannot be trusted.
- `active_sessions` in `ws.py` is in-process (documented `--workers 1` constraint); a backend restart also resets all `is_reconnect` flags, compounding Scenario 1.
