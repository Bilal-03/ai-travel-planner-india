# YatraAI implementation roadmap

This roadmap mirrors the delivery order in the master implementation plan.
The Phase 0 audit is the only phase executed on this branch.

## Phase status

| Phase | Focus | Status at Phase 0 close |
| --- | --- | --- |
| 0 | Audit, documentation, safety baseline, fixtures, and tests | Complete on `codex/phase-0-audit-baseline` |
| 1 | Common provenance, freshness, provider-neutral response models | Not started |
| 2 | Durable trip jobs, Redis events, resumable progress, idempotency | Not started |
| 3 | Deterministic constraint engine and scoped itinerary refinement | Not started |
| 4 | Stardrift-inspired but simple trip workspace UX | Not started |
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

Do not start Phase 1 until the Phase 0 completion report has been reviewed.
Phase 1 should first define and test the provenance contract, then introduce
provider-neutral transport/place/weather/route models and visible frontend
status components. It must preserve the current fallback providers and
generation flow while making estimated/static/unavailable states explicit.

## Later sequencing constraints

1. Phase 2 depends on a stable current response contract and should not be
   combined with the Phase 1 UI/status work.
2. Phase 3 depends on durable provider-neutral inputs and should validate
   feasibility before adding richer narration.
3. Phase 4 follows accuracy/reliability work; it is not an initial visual
   redesign task.
4. Phase 5 must preserve the current provider until each replacement is
   contract-tested and feature-flagged.
5. Multi-city, accounts, collaboration, offline, analytics, and payments stay
   outside the initial single-destination product scope.

## Delivery controls

Every future phase should have its own `codex/phase-N-*` branch, focused tests,
documented environment/migration changes, known limitations, and a clean git
commit before the next phase begins.
