# YatraAI implementation roadmap

This roadmap mirrors the delivery order in the master implementation plan.
Phases 0, 1, 2, 3, and 4 are complete on their respective branches. Phase 5 is
the next implementation boundary.

## Phase status

| Phase | Focus | Status |
| --- | --- | --- |
| 0 | Audit, documentation, safety baseline, fixtures, and tests | Complete on `codex/phase-0-audit-baseline` |
| 1 | Common provenance, freshness, provider-neutral response models | Complete on `codex/phase-1-data-trust` |
| 2 | Durable trip jobs, Redis events, resumable progress, idempotency | Complete on `codex/phase-2-durable-generation` |
| 3 | Deterministic constraint engine and scoped itinerary refinement | Complete on `codex/phase-3-constraint-planner` |
| 4 | Stardrift-inspired but simple trip workspace UX | Complete on `codex/phase-4-trip-workspace` |
| 5 | Provider gateway and live travel integrations | Not started |
| 6 | Multi-destination trips, accounts, and explicit preference memory | Not started |
| 7 | Offline access, collaboration, analytics, security, and production hardening | Not started |

## Phase 0 exit evidence

- Current frontend routes, backend endpoints, models, providers, AI flow,
  persistence, cache, progress, deployment, and environment handling are
  documented.
- Ten anonymised request fixtures and ten deterministic response-contract
  fixtures are checked in under `backend/tests/fixtures/`.
- `backend/tests/test_baseline_fixtures.py` runs the current generation
  orchestration against provider/Gemini stubs and validates the response
  contract for all ten scenarios.
- Existing backend tests and frontend lint remain green.
- The existing Playwright journey remains green when the local server is
  allowed to bind outside the restricted sandbox.
- The production build limitation is recorded: Next/font needs network access
  to fetch Google Fonts in this environment.

## Phase 1 gate

Phase 1 is complete after defining and testing the provenance contract,
introducing provider-neutral metadata on transport/place/weather/route/meal/
budget models, adding visible frontend status components, and preserving the
current fallback providers and generation flow. See
`docs/phase-1-completion-report.md` for the exit evidence and limitations.

## Phase 2 gate

Phase 2 is complete after moving the primary frontend generation path to
asynchronous trip jobs with Redis-backed snapshots, queue claims, event replay,
idempotency, cancellation, controlled retry, and a persisted browser resume
record. Completed itineraries still use the existing PostgreSQL-compatible trip
store, and the legacy synchronous endpoint remains available for compatibility.
See `docs/phase-2-completion-report.md` for the exit evidence and known
operational limitations.

## Phase 3 gate

Phase 3 is complete after introducing the structured `TripIntent` contract, a
deterministic candidate scheduler and validator for pace, opening hours, travel
time, transport windows, weather, accessibility, mandatory/excluded places, and
budget, plus server-side scoped refinement for affected days and legs. Gemini
now receives a deterministic candidate schedule before narration, and the
existing final route/budget validation remains authoritative. See
`docs/phase-3-completion-report.md` for the exit evidence and limitations.

## Phase 4 gate

Phase 4 is complete after adding a quick natural-language planning brief with a
reviewable detailed form, a responsive trip workspace, mobile Plan/Map/Budget/
Chat tabs, server-validated activity editing, recommendation explanations,
transport comparisons, and one-step server-side undo. The workspace preserves
the durable generation, provenance, and deterministic constraint contracts from
Phases 1–3. See `docs/phase-4-completion-report.md` for the exit evidence and
known limitations.

## Later sequencing constraints

1. Phase 4 follows accuracy/reliability work; it is not an initial visual
   redesign task.
2. Phase 5 must preserve the current provider until each replacement is
   contract-tested and feature-flagged.
3. Multi-city, accounts, collaboration, offline, analytics, and payments stay
   outside the initial single-destination product scope.

## Delivery controls

Every future phase should have its own `codex/phase-N-*` branch, focused tests,
documented environment/migration changes, known limitations, and a clean git
commit before the next phase begins.
