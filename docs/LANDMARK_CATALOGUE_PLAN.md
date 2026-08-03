# India landmark catalogue plan

## Objective

Give every supported Indian destination a reviewed, ranked shortlist of
destination-defining places. The itinerary planner must use this shortlist as
its primary landmark input; a language model may sequence eligible places, but
must not create landmark facts or claim current operational details.

## Product rule

For each destination, present a practical number of high-priority places that
fits the trip length, travel mode, budget, stated preferences, and travel time.
Do not promise that every landmark can be visited on every trip.

The catalogue is the source of truth for editorial prominence. Mutable facts
such as opening hours, ticket prices, ferry operation, closures, and crowding
must be separately sourced and visibly labelled with retrieval/review time.

## Catalogue record

Each landmark record must contain:

- `destination_id` and official display name
- verified latitude and longitude
- category and accessibility-relevant visit profile
- editorial priority rank within the destination
- conservative estimated visit duration and INR cost band, labelled estimated
- official/source URL, source publisher, review date, and provenance type
- constraints and dependencies, such as a ferry, timed entry, or seasonal risk
- `active`, `review_due_at`, and source-kill-switch fields

Records must preserve official place names. Any Hindi or Hinglish display copy
must be verified separately.

## Data sources and source policy

1. Prefer official state tourism departments, destination authorities, ASI,
   UNESCO, and other authoritative heritage bodies.
2. Use OpenStreetMap or a similarly licensed geographic source only for map
   geometry after licence and attribution review.
3. Do not scrape travel-guide pages or ask the language model to browse and
   invent a list. They may be used as research leads only when a reviewer
   verifies the final record against an allowed source.
4. Store source attribution and review metadata with each record. If a source
   becomes unavailable or its terms are unsuitable, disable affected records
   rather than silently retaining stale claims.

TripAdvisor may be consulted manually to identify commonly sought attractions
and traveller-intent categories. Its rankings, reviews, images, and text must
not be scraped, stored, displayed, or treated as a catalogue source unless a
separate licence and provider review is approved.

## Planner behaviour

1. Load ranked landmark records for the chosen destination.
2. Filter only by deterministic constraints: date, trip length, user-selected
   modes, explicit access needs, estimated budget, and known dependencies.
3. Send the remaining records, their rank, visit duration, and restrictions to
   the language model for sequencing and narrative only.
4. Validate every planned activity against the selected catalogue record and
   deterministic timing/budget rules. Do not accept invented landmark names or
   coordinates.
5. Explain omitted high-priority places where a known constraint makes them
   impractical; otherwise retain them as alternatives.

## Coverage rollout

### Phase 1 — foundation

- Define the versioned catalogue schema and source-review workflow.
- Seed the currently supported city list with destination metadata only.
- Add source provenance, freshness, and attribution fields before displaying
  editorial rankings.

### Phase 2 — reviewed high-demand destinations

- Curate 8–12 core landmarks each for the highest-demand domestic destinations.
- Include explicit practical dependencies such as Elephanta ferry travel.
- Add tests that enforce priority ordering, provenance, and no-invented-place
  validation.

### Phase 3 — full supported-city coverage

- Expand in reviewed regional batches until every supported destination has a
  useful shortlist.
- Publish a coverage label where a destination is not yet fully reviewed.

## Non-goals for this catalogue

- It is not live inventory, booking, or a guarantee of admission.
- It is not a demographic safety score.
- It does not replace a live source for weather, closures, transport, or hours.
