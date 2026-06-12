# Sprint 6 UX Review — BOBB AI Frontend
**Reviewer**: Senior UX Architect perspective  
**Date**: 2026-06-12  
**Scope**: All 13 frontend screens + WebSocket integration  
**Focus**: User experience and conversion. Code quality excluded.

---

## Executive Summary

Sprint 6 delivers a structurally sound kiosk experience with strong brand consistency and appropriate use of motion. The critical UX gaps cluster around three themes: **irreversible destructive actions** (Start Over wipes an entire pipeline with one tap), **processing states that leave the customer in the dark** (ThinkingScreen has no estimated time, GeneratingScreen has no images to look at), and **late-funnel friction** (Refinement requires already knowing what you want before you've seen anything). None are architectural rewrites — all are screen-level fixes.

---

## 1. Story Collection Friction

### 🔴 Critical — "Start Over" on the Preview screen destroys all work without confirmation

**Screen**: `PreviewScreen.tsx`  
**Element**: "Start Over" button in the action bar  
**Behaviour**: Calls `setState(SessionState.LISTENING)`, which navigates back to the text input. The store's `latestDesign`, `generatingProgress`, and any selected variant are **not cleared** — but the customer is effectively restarting the AI pipeline. When they submit again, `setLatestDesign` overwrites the previous design with no recovery path.

From a kiosk conversion standpoint this is catastrophic. A customer who spent 10 minutes generating variants, accidentally taps "Start Over" (positioned next to the CTA), and their entire session is gone. No confirmation dialog, no warning, no "are you sure?". For a physical-goods purchase where the pipeline takes 20-25 seconds to re-run, this will cause visible distress and staff intervention.

**Fix**: Replace the bare `setState(LISTENING)` with a confirmation sheet (two large touch targets: "Yes, start fresh" / "No, keep my designs"). On tablets, a bottom sheet modal sized for thumbs is appropriate.

---

### 🟠 High — Character counter provides negative feedback before the customer has finished typing

**Screen**: `ListeningScreen.tsx`, lines 111–113  
**Element**: `"{10 - charCount} more characters needed"` under the textarea  

This message appears from character 0. A customer who types slowly sees a nagging counter throughout their natural pausing rhythm. The phrasing "more characters needed" frames their story as insufficient before they've attempted to share it — a significant emotional mis-signal for a product built around personal storytelling.

The 10-character minimum is a backend guard, not a UX signal. Showing it continuously degrades the invitation.

**Fix**: Show the counter only after a submit attempt with an insufficient story, not pre-emptively. Replace with affirming micro-copy like "Keep going — the more detail, the better your design."

---

### 🟡 Medium — Example prompts disappear the moment the customer starts typing

**Screen**: `ListeningScreen.tsx`  
**Condition**: `{!storyText && (...)}` — examples render only when `storyText` is empty  

A customer who taps an example prompt to use as a starting point and then edits it loses all examples as soon as they type their first character. This is fine for power users but disorienting for first-time kiosk customers, who may want to reference the examples mid-edit.

**Fix**: Show examples until the customer has typed at least 40 characters (enough to confirm they're writing their own story). Or restructure as a single floating "inspiration" chip that expands on tap, preserving the textarea surface area.

---

### 🟢 Low — "Step 1 of 3" step counter is inconsistent with the full journey

**Screen**: `ListeningScreen.tsx`, `ThinkingScreen.tsx`, `GeneratingScreen.tsx`  
The journey has 13 states and ~7 meaningful customer-facing steps. Labelling the first three screens as "1 of 3" and then stopping at "3 of 3" on GeneratingScreen leaves the customer with no progress context across Product Selection, Cart, Checkout, and Production — which together represent the most anxiety-prone phase (money changing hands, waiting for a physical object).

**Fix**: Either extend the step model consistently through all phases (1–5: Story → Designs → Product → Checkout → Print), or drop the step counter entirely in favour of a continuous progress indicator in a persistent header.

---

## 2. Processing States

### 🔴 Critical — ThinkingScreen provides no time estimate; customers have no frame of reference

**Screen**: `ThinkingScreen.tsx`  
The screen shows a spinner, bouncing dots, and four rotating phrases. There is no indication of how long this will take. The docs specify "20-25 seconds total AI processing." In a kiosk context, 8–12 seconds of opaque loading after a Submit tap — with no time anchor — crosses the "is this broken?" threshold for most users.

Critically, the cycling phrase animation has a design bug: each phrase is `position: absolute` inside an `overflow-hidden` container but there is no explicit `position: relative` on the parent `motion.div`. The phrases stack on top of each other rather than cycling cleanly. Customers may see overlapping text during transitions.

**Fix**: Add a `relative` wrapper around the phrase carousel. Add a progress bar or a simple "Usually 8–12 seconds" line below the dots. The bar need not be accurate — a determinate-looking animation from 0–100% over 10 seconds sets expectations without requiring backend integration.

---

### 🟠 High — GeneratingScreen shows placeholder grid cells but no design previews as they arrive

**Screen**: `GeneratingScreen.tsx`  
The 2×2 grid shows style names and a gold checkmark when a variant completes. The WS `variant_ready` event carries `image_url` — but `GeneratingScreen` does not render it. The customer watches four grey boxes tick off with checkmarks, then transitions to `PreviewScreen` to see the actual images.

This is a missed delight moment. The designs appearing one by one — folk art, then geometric, then watercolour — would be the most emotionally engaging moment in the entire journey. Currently it's a progress bar with labels.

**Fix**: In the 2×2 grid, render `<img src={variant.image_url} />` inside each cell as variants arrive from the store. This requires reading `latestDesign.variants` from the store in `GeneratingScreen`. The store already has the data via `addVariant`; the screen just doesn't use it.

---

### 🟡 Medium — ThinkingScreen and GeneratingScreen have no "something went wrong" recovery path

**Screens**: `ThinkingScreen.tsx`, `GeneratingScreen.tsx`  
Both screens are passive — they show loading states and wait for `ListeningScreen.handleSubmit()` to resolve. If the backend times out or returns an error after transitioning to `THINKING`, the error handler in `ListeningScreen` calls `setState(SessionState.LISTENING)`, snapping the customer back to the story input without any explanation of what happened.

The screen transition fires, the customer lands on the story input, and sees their text still there with no error message — because `setError` in `ListeningScreen` has no effect after the component has unmounted.

**Fix**: Surface errors via a toast/overlay that persists across state transitions, or move error state into the global store rather than local component state. The customer needs to know *why* they're back at the story screen.

---

## 3. Variant Gallery Usability

### 🟠 High — Refinement button is disabled until a variant is selected; discoverability is broken

**Screen**: `PreviewScreen.tsx`, line 62  
```tsx
disabled={!activeId || loadingRecs}
```
The "Refine (N left)" button sits in the top-right header and is greyed out until the customer selects a variant. This is the correct guard, but it means customers encounter a disabled button before they understand the interaction model — tap a variant first, then refine is unlocked.

There is no tooltip, no disabled-state label change, and no visual affordance indicating *why* the button is disabled. On a tablet, a greyed ghost button with no explanation looks like a broken UI element.

**Fix**: Either keep the button always enabled and show a prompt ("Select a design first to refine it") when tapped without a selection, or add a helper text label under the button: "Select a design to enable." The second option preserves the guard without confusing the customer.

---

### 🟡 Medium — No way to zoom or inspect a variant before committing

**Screen**: `PreviewScreen.tsx`  
`VariantCard` renders at `aspect-square` within a 2-column grid. On a 13-inch tablet the cards are approximately 200×200px — large enough to appreciate style but not detail. For a design going on a garment, customers will want to inspect the print artwork at full resolution before selecting.

There is no tap-to-expand / lightbox path.

**Fix**: Add a long-press (500ms) or a small expand icon to each `VariantCard` that opens the image full-screen with a close button. This does not need to affect the selection state.

---

### 🟢 Low — "Refined" badge on VariantCard has no visual differentiation of *which* is refined vs original

**Component**: `VariantCard.tsx`, line 72  
The green "Refined" badge appears on `is_refined` variants. In a grid that may contain both original and refined variants (after refinement, the store appends the new variant alongside originals), the customer may not understand the relationship — especially if they refined twice and have 5–6 cards.

**Fix**: Group variants: originals first, refined variants below a thin divider labelled "Your Refinements." Or show the parent style name on the "Refined" badge: "Refined · Folk Art."

---

## 4. Refinement Discoverability

### 🟠 High — Refinement requires a pre-selected variant but the CTA that takes you there doesn't explain this

**Screen**: `PreviewScreen.tsx` → `RefiningScreen.tsx`  
The refinement flow requires `selectedVariantId` to exist (used as the source for the refine API call). If the customer arrives at RefiningScreen without having selected a variant, `selectedVariantId` falls back to `latestDesign?.variants[0]?.variant_id` — the first variant — silently. The customer has no idea which design they're refining.

This is a correctness-adjacent UX issue: a customer who selects variant 3 (Watercolour) and then taps "Refine" will refine variant 1 (Folk Art) if they're on a fresh load and haven't explicitly tapped a card yet.

**Fix**: Always show the variant being refined at the top of RefiningScreen — a thumbnail of the source variant with its style label. This confirms the customer's intent and eliminates the silent fallback ambiguity.

---

### 🟡 Medium — Refinement options are abstract; customers won't know what "More Premium" means before tapping

**Screen**: `RefiningScreen.tsx`  
Options like "More Premium" and "More Cultural" are meaningful to a designer but opaque to a first-time kiosk customer. Each has a one-line description ("Elevated, luxury feel"), but on a small button there's no way to preview the effect before spending a refinement.

With only 3 refinements available per session (a hard limit displayed on screen), customers will hesitate or pick randomly.

**Fix**: Add a "before/after" concept — small example images or colour swatches for each refinement type that illustrate the visual direction. Even an illustrative icon set (not photographs) would reduce cognitive load. Alternatively, rename options to customer-friendly outcomes: "Make it feel more traditional" instead of "More Cultural."

---

### 🟢 Low — Refinement count is decremented client-side without synchronisation

**Screen**: `RefiningScreen.tsx`, line 69  
`3 - (latestDesign?.refinements_count ?? 0)` — the count is derived from `latestDesign.refinements_count`, which is set to `0` at design initialisation and never updated by the API response from `api.refineVariant()`. The count will always show "3 refinements remaining" across the full session unless the backend sends a `state_change` event or the session is recovered from PostgreSQL.

A customer could tap "Apply Refinement" three times and always see "3 remaining."

**Fix**: Update `refinements_count` in the store after each successful refine call, either from the API response (add it to the `RefineResponse` type) or by incrementing it locally in `RefiningScreen.handleRefine()`.

---

## 5. Recommendation Clarity

### 🟡 Medium — Score percentage ("87%") has no explained basis; customers may not trust it

**Component**: `ProductCard.tsx`, lines 52–62  
The animated score bar and percentage figure ("Best Match — 87%") are visually prominent but unexplained. In a retail context, customers will wonder "87% of what?" — is it a satisfaction score, a stock level, a match quality?

The `reasons` list beneath provides the actual rationale, but the score number appears first and without context.

**Fix**: Replace or label the score: "87% design match" or simply remove the raw percentage and keep only the bar as a relative visual comparison between the three options. The `reasons` list is more persuasive than a decontextualised number.

---

### 🟡 Medium — "Low Stock" badge creates urgency without giving actionable information

**Component**: `ProductCard.tsx`, line 40  
The red "Low Stock" badge appears when `rec.low_stock === true`. It creates urgency (intentionally), but on a kiosk there is no alternative if the stock runs out — the customer cannot buy online or reserve. Showing "Low Stock" without context ("Only 2 left" or "Ask a team member") may cause anxiety without enabling a decision.

**Fix**: Change the label to "Almost Gone — ask staff" or suppress it entirely if the count is above a safe threshold. Alternatively, if `units_available` is in the data, show it directly: "3 remaining."

---

### 🟢 Low — Production time is shown but not contextualised against the customer's remaining wait

**Component**: `ProductCard.tsx`, lines 85–87  
"10 minutes production" is displayed on each card. In isolation this is useful. But the customer has already been in the journey for several minutes and doesn't know their cumulative wait. If the store is busy, this number may not reflect queue depth.

**Fix**: If queue data is available, show estimated ready time ("Ready by ~3:45 PM") instead of raw minutes. If not, add a note: "Plus any current queue time — ask a team member."

---

## 6. Mobile/Tablet Ergonomics

### 🟠 High — Primary CTAs are not consistently in the thumb zone for a held-upright tablet

**Screens**: `GreetingScreen.tsx`, `ListeningScreen.tsx`, `PreviewScreen.tsx`  
On the Samsung Tab S9 Ultra (14.6-inch screen), the primary action buttons are positioned at the bottom of a flex column using `mt-auto` or end-of-content natural flow. This is correct in principle, but several screens have the CTA at the very bottom of a page that requires vertical scrolling to reach — particularly `ListeningScreen` when the example prompts render below the textarea.

The `min-h-screen` layout with `justify-center` works well on short content but can push CTAs off-screen when content grows (e.g., examples list + error message + counter simultaneously visible).

**Fix**: Pin the CTA bar to the bottom of the viewport (`fixed bottom-0` or `sticky bottom-0 bg-bobb-cream`) so it remains reachable regardless of content height. This is especially critical for `ListeningScreen` and `ProductSelectionScreen` (three ProductCards can easily exceed viewport height).

---

### 🟡 Medium — Touch targets on refinement options are undersized for gloved or hurried hands

**Screen**: `RefiningScreen.tsx`  
Refinement option cards use `p-4` padding with `rounded-card`. In a 2-column grid this yields approximately 160×120px per target on a 13-inch tablet — above the 44px minimum but below the comfortable 80px minimum recommended for kiosk/retail environments where customers may be standing, moving, or stressed.

The button font size is `text-sm` (14px) for the label and `text-xs` (12px) for the description — both below comfortable reading size for a standing customer.

**Fix**: Increase card height to at least 140px. Bump label to `text-base`, description to `text-sm`. On a 2-column grid with `gap-3` this remains comfortable without requiring a layout change.

---

### 🟢 Low — No landscape-mode consideration

**All screens**  
All layouts assume portrait orientation (`min-h-screen` vertical flex). The Samsung Tab S9 Ultra is commonly held in landscape at retail counters. In landscape, the `max-w-2xl` content columns become narrow strips on a 16:9 canvas, and the 2×2 variant grid becomes awkwardly small.

**Fix**: Add a single Tailwind breakpoint (`md:flex-row`, `md:grid-cols-4`) on the variant gallery and product list for landscape orientation. The listening screen textarea should fill available width in both orientations.

---

## 7. Session Recovery UX

### 🟠 High — Session recovery silently resumes at a mid-journey screen with no re-orientation for the customer

**Hook**: `useWebSocket.ts`, `session_resumed` handler  
When a session is reconnected (power cycle, tablet sleep, staff restart), the `session_resumed` WS event sets `currentState` to whatever state was inferred from the DB — potentially `PREVIEW` or `PRODUCT_SELECTION`. The customer (or a *different* customer at a shared kiosk) is dropped directly into the middle of a design flow with no context.

There is no "Welcome back" interstitial, no explanation of what was recovered, and no offered option to start fresh. A new customer picking up an abandoned kiosk will see someone else's designs without any system explanation.

**Fix**: On `session_resumed` with `is_reconnect: true` and a non-idle state, render a brief `SessionResumeOverlay` (full-screen modal) for 3 seconds:
- "We found your previous session" with a thumbnail of the design
- Two options: "Continue" and "Start Fresh"
- Auto-continue after 8 seconds of no interaction

This is both a conversion win (retained state reduces re-generation time) and a kiosk hygiene feature (prevents state bleed between customers).

---

### 🟡 Medium — WebSocket reconnect backoff is silent; the customer has no offline indicator

**Hook**: `useWebSocket.ts`, exponential backoff to 15s  
When the WS disconnects and enters the backoff loop, `setWsConnected(false)` is called in the store, but no screen reads `wsConnected` to surface a visual indicator. A customer mid-journey during a network glitch will see a frozen state with no explanation. They will tap buttons that trigger API calls, which may succeed or fail silently.

**Fix**: Add a thin persistent banner (top of screen, 32px, amber background) that appears when `wsConnected === false`: "Reconnecting… your progress is safe." Dismiss it automatically when WS reconnects. This is a 10-line change across `App.tsx` and a new `ConnectionBanner` component.

---

### 🟢 Low — ClarifyingScreen is wired in the state machine but has no path into it from the live flow

**Screen**: `ClarifyingScreen.tsx`  
`ListeningScreen.handleSubmit()` checks `storyResp.needs_clarification` but always proceeds to `THINKING` regardless of the value. The `CLARIFYING` state and screen exist, but the transition `LISTENING → CLARIFYING` is never triggered in the current code. The screen is dead.

**Fix**: After `submitStory`, if `storyResp.needs_clarification === true`, call `setState(SessionState.CLARIFYING)` and return early (don't call `generateDesign` yet). Add a "Continue Anyway" path from `ClarifyingScreen` that calls `generateDesign` with the existing story. This restores the intended flow documented in the architecture spec.

---

## Summary Table

| # | Finding | Screen | Severity |
|---|---------|--------|----------|
| 1 | "Start Over" destroys pipeline without confirmation | PreviewScreen | 🔴 Critical |
| 2 | ThinkingScreen has no time estimate; phrase animation has layout bug | ThinkingScreen | 🔴 Critical |
| 3 | Negative "more characters needed" counter appears before typing | ListeningScreen | 🟠 High |
| 4 | GeneratingScreen doesn't show images as they arrive from WS | GeneratingScreen | 🟠 High |
| 5 | Refinement button disabled with no explanation of why | PreviewScreen | 🟠 High |
| 6 | Refinement silently falls back to variant[0] instead of selected | RefiningScreen | 🟠 High |
| 7 | Session recovery drops customer mid-journey with no re-orientation | useWebSocket | 🟠 High |
| 8 | Primary CTAs not pinned to viewport; scroll required on long content | ListeningScreen, ProductSelectionScreen | 🟠 High |
| 9 | Score percentage unexplained | ProductCard | 🟡 Medium |
| 10 | Refinements count never decrements client-side | RefiningScreen | 🟡 Medium |
| 11 | WS disconnect has no offline indicator | App / useWebSocket | 🟡 Medium |
| 12 | Refinement options abstract; no preview of effect | RefiningScreen | 🟡 Medium |
| 13 | Example prompts vanish on first keystroke | ListeningScreen | 🟡 Medium |
| 14 | No zoom/lightbox for variant inspection | PreviewScreen / VariantCard | 🟡 Medium |
| 15 | CLARIFYING state exists but is never triggered | ListeningScreen | 🟡 Medium |
| 16 | "Low Stock" creates urgency without actionable info | ProductCard | 🟡 Medium |
| 17 | Touch targets in RefiningScreen below kiosk-comfortable minimum | RefiningScreen | 🟡 Medium |
| 18 | Step counter stops at "3 of 3" and disappears after Generate | Multiple | 🟢 Low |
| 19 | "Refined" badge doesn't indicate relationship to parent variant | VariantCard | 🟢 Low |
| 20 | Production time shown without queue context | ProductCard | 🟢 Low |
| 21 | No landscape-mode layout consideration | All screens | 🟢 Low |

---

## Priority Order for Next Sprint

**Fix these first** (unblocks conversion, prevents customer distress):
1. Confirmation dialog on "Start Over"
2. ThinkingScreen time estimate + animation layout fix
3. CTA sticky/pinned to bottom of viewport
4. Session recovery overlay (is_reconnect interstitial)

**Fix these second** (improves journey quality):
5. GeneratingScreen: render images as variants arrive
6. Refinement: always show source variant thumbnail
7. Refinement: fix count decrement
8. CLARIFYING flow: wire the actual transition
9. WS offline banner

**Fix these in polish sprint**:
10–21 as bandwidth allows.
