# YatraAI Phase 3 completion report

Date: 2026-08-04
Branch: `codex/phase-3-constraint-planner`

Phase 3 is complete. YatraAI now has a structured planning intent and a
deterministic constraint layer that runs before Gemini narration. The existing
itinerary response remains compatible, while timings, candidate places,
transport windows, budgets, and refinements receive server-side checks.

## Delivered

- Added `TripIntent` to the backend model contract, including destinations,
  traveller types, budget/currency, pace, interests, diet, accessibility,
  transport/hotel preferences, travel windows, mandatory/excluded places, and
  free-text notes.
- Added the deterministic `ConstraintEngine` in
  `backend/app/services/constraint_engine.py`.
- Added machine-readable scheduling for reviewed POIs with visit duration,
  opening hours, meal breaks, travel buffers, pace limits, weather suitability,
  accessibility evidence, mandatory/excluded place handling, transport arrival /
  departure windows, daily budgets, and deterministic total-cost trimming.
- Added a deterministic candidate schedule to the Gemini prompt. Gemini can add
  descriptions, notes, meals, tips, and explanations, while canonicalization,
  route reflow, final validation, and budget arithmetic remain server-owned.
- Added structured refinement parsing for common edits including lighter days,
  budget reduction, later mornings, place replacement/addition, and transport
  switches. Targeted changes preserve unrelated days and are revalidated.
- Added backend request/itinerary fields and frontend controls for must-visit
  places, excluded places, and planner notes.
- Added transport-edit validation for arrival/departure windows and budget
  impact; invalid transport selections are rejected server-side.

## Verification

- Backend full suite: `58 passed`.
- Phase 3 engine/refinement tests: `6 passed`.
- Frontend lint: passed.
- Frontend production build: passed.
- Mocked Playwright journey: `1 passed`.
- No new database migration or environment variable is required.
- `git diff --check` is required before commit.

## Known limitations

- The current product remains single-destination. The `destinations` list in
  `TripIntent` is future-ready, but multi-city movement belongs to Phase 6.
- Hotel candidates do not yet come from a provider; the constraint layer uses
  the existing accommodation preference and deterministic stay-rate estimate.
- Candidate scheduling uses a conservative geometry-based travel estimate. The
  existing OSRM path still supplies final route segments and validation when
  available, with a labelled fallback when it is not.
- Accessibility and opening-hours constraints are only as strong as the
  candidate metadata. Unknown accessibility is not presented as confirmed.
- Natural-language refinements outside the supported deterministic patterns
  still use Gemini, but only affected days are merged back and the full result
  is revalidated.
- The frontend now collects the new intent fields, but a future conversational
  intent layer can make richer natural-language extraction more expressive.

## Phase boundary

Phase 4 is next: build the simple Stardrift-inspired trip workspace UX around
the durable generation and accuracy contracts. Preserve the deterministic
constraint layer and job recovery behavior while improving trip editing,
comparison, and presentation flow.
