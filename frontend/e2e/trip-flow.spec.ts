import { expect, test } from "@playwright/test";

function plusDays(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function itinerary() {
  const start = plusDays(10);
  const end = plusDays(12);
  const train = {
    mode: "train",
    provider: "Indian Railways fare estimate",
    code: null,
    price: 900,
    duration_minutes: 300,
    departure_time: null,
    arrival_time: null,
    departure_city: "Delhi",
    arrival_city: "Jaipur",
    is_recommended: true,
    is_fallback: true,
    field_provenance: { fare: "Estimated 3A fare", availability: "Not available" },
    field_data_provenance: {
      fare: { provider: "YatraAI estimate", status: "estimated", retrieved_at: "2026-08-03T12:00:00Z", expires_at: "2026-08-04T12:00:00Z", confidence: 0.45, source_reference: "app://transport/fallback-trains", disclaimer: "Verify before booking." },
      availability: { provider: "not_provided", status: "unavailable", retrieved_at: null, expires_at: null, confidence: null, source_reference: null, disclaimer: "Availability was not provided; verify before booking." },
    },
    provenance: { provider: "YatraAI static train catalogue", status: "static_reference", retrieved_at: "2026-08-03T12:00:00Z", expires_at: "2027-02-03T00:00:00Z", confidence: 0.55, source_reference: "app://transport/fallback-trains", disclaimer: "Static schedule reference; verify before booking." },
    availability_status: "Not available",
    last_checked_at: "2026-08-03T12:00:00Z",
  };

  return {
    id: "e2e-trip-123",
    origin: { name: "Delhi", state: "Delhi", coordinates: { lat: 28.6139, lng: 77.209 }, iata_code: "DEL", station_code: "NDLS" },
    destination: { name: "Jaipur", state: "Rajasthan", coordinates: { lat: 26.9124, lng: 75.7873 }, iata_code: "JAI", station_code: "JP" },
    start_date: start,
    end_date: end,
    total_days: 3,
    members: 2,
    planning_notes: "heritage places",
    places: [],
    items: [],
    transport_options: [train],
    selected_transport: train,
    day_plans: [{
      day_number: 1,
      date: start,
      weather: null,
      transport: null,
      activities: [{ poi: { id: "amber", name: "Amber Fort", category: "fort", coordinates: { lat: 26.9855, lng: 75.8513 }, estimated_visit_minutes: 120, estimated_cost: 500, description: null, opening_hours: "09:00-17:00", provenance: { provider: "Ministry of Tourism", status: "static_reference", retrieved_at: "2026-08-03T00:00:00Z", expires_at: "2027-02-03T00:00:00Z", confidence: 0.9, source_reference: "https://www.incredibleindia.gov.in/", disclaimer: "Verify current access and hours before visiting." }, field_provenance: { estimated_cost: { provider: "YatraAI estimate", status: "estimated", retrieved_at: "2026-08-03T00:00:00Z", expires_at: "2027-02-03T00:00:00Z", confidence: 0.55, source_reference: "app://poi-estimates", disclaimer: "Verify current admission before visiting." } } }, start_time: "10:00", end_time: "12:00", estimated_cost: 500, notes: null, is_backup: false }],
      meals: [{ name: "Suggested meal type: Rajasthani thali", cuisine: "Rajasthani", meal_type: "lunch", estimated_cost: 300, notes: "Choose a trusted local restaurant.", provenance: { provider: "YatraAI planning estimate", status: "estimated", retrieved_at: "2026-08-03T00:00:00Z", expires_at: null, confidence: 0.45, source_reference: "app://yatraai-planning-estimates", disclaimer: "Verify the restaurant and current menu before dining." }, field_provenance: { estimated_cost: { provider: "YatraAI planning estimate", status: "estimated", retrieved_at: "2026-08-03T00:00:00Z", expires_at: null, confidence: 0.45, source_reference: "app://yatraai-planning-estimates", disclaimer: "Verify the current menu before dining." } } }],
      backup_activities: [],
      day_budget: 1200,
      day_spent: 800,
      local_transport_minutes: 30,
      local_transport_cost: 120,
      notes: "Explore Amber Fort.",
    }],
    budget: { outbound_transport: 1800, return_transport: 1800, transport: 3600, food: 600, activities: 1000, local_transport: 500, taxes_buffer: 285, miscellaneous: 0, total_estimated: 5985, remaining: 4015, provenance: { provider: "YatraAI deterministic budget calculator", status: "estimated", retrieved_at: "2026-08-03T00:00:00Z", expires_at: null, confidence: 0.9, source_reference: "app://budget-calculator", disclaimer: "Verify live prices, taxes, and booking fees before purchase." } },
    route_segments: [],
    plan_options: [{ id: "plan-1", title: "Essential highlights", description: "A focused route.", day_plans: [], budget: { outbound_transport: 1800, return_transport: 1800, transport: 3600, food: 600, activities: 1000, local_transport: 500, taxes_buffer: 285, miscellaneous: 0, total_estimated: 5985, remaining: 4015 }, route_segments: [], generation_notes: [] }],
    selected_plan_id: "plan-1",
    weather_forecast: [],
    destination_photos: [],
    festivals: [],
    packing_list: [],
    share_url: null,
    generation_notes: ["Confirm tickets before booking."],
  };
}

test("plans a trip and opens a read-only shared itinerary", async ({ page }) => {
  const trip = itinerary();
  const place = {
    id: "place-city-palace",
    name: "City Palace",
    category: "palace",
    coordinates: { lat: 26.9258, lng: 75.8237 },
    address: null,
    city: "Jaipur",
    state: "Rajasthan",
    country: "India",
    description: "A palace complex in Jaipur's historic centre.",
    opening_hours: null,
    rating: null,
    review_count: null,
    price_level: null,
    estimated_visit_minutes: 120,
    estimated_cost: 400,
    official_url: null,
    maps_url: "https://www.google.com/maps/search/?api=1&query=26.9258,75.8237",
    provider_ids: { yatraai: "place-city-palace" },
    photos: [],
  };
  type MutableTrip = Omit<typeof trip, "places" | "items"> & { places: Array<typeof place>; items: Array<Record<string, unknown>> };
  const mutableTrip = JSON.parse(JSON.stringify(trip)) as MutableTrip;
  const job = {
    id: "e2e-job-123",
    status: "accepted",
    step: "accepted",
    message: "Your trip request was accepted.",
    progress: 0,
    result_trip_id: null,
    error: null,
    attempts: 0,
    cancel_requested: false,
    created_at: "2026-08-03T12:00:00Z",
    updated_at: "2026-08-03T12:00:00Z",
    completed_at: null,
  };
  await page.route("**/health", (route) => route.fulfill({ json: { status: "healthy", services: {} } }));
  await page.route("**/api/search/cities?*", (route) => {
    const city = new URL(route.request().url()).searchParams.get("q")?.toLowerCase() || "";
    const result = city.includes("jaipur")
      ? { name: "Jaipur", state: "Rajasthan", display_name: "Jaipur, Rajasthan", coordinates: { lat: 26.9124, lng: 75.7873 } }
      : { name: "Delhi", state: "Delhi", display_name: "Delhi, Delhi", coordinates: { lat: 28.6139, lng: 77.209 } };
    return route.fulfill({ json: [result] });
  });
  await page.route("**/api/planner/clarify", (route) => route.fulfill({ json: {
    status: "ready",
    brief: { origin: "Delhi", destination: "Jaipur", start_date: trip.start_date, end_date: trip.end_date, budget: 10000, members: 2, transport_mode: "train", planning_notes: "heritage places" },
    questions: [],
    trip_request: { origin: "Delhi", destination: "Jaipur", start_date: trip.start_date, end_date: trip.end_date, budget: 10000, transport_mode: "train", members: 2, planning_notes: "heritage places" },
  }}));
  await page.route("**/api/trip-jobs", (route) => route.fulfill({ json: job, status: 202 }));
  await page.route("**/api/trip-jobs/e2e-job-123", (route) => route.fulfill({ json: { ...job, status: "completed", step: "completed", message: "Your itinerary is ready.", progress: 100, result_trip_id: trip.id } }));
  await page.route("**/api/trip-jobs/e2e-job-123/events**", (route) => route.fulfill({
    status: 200,
    contentType: "text/event-stream",
    body: `id: 1\nevent: progress\ndata: ${JSON.stringify({ id: 1, job_id: job.id, status: "completed", step: "completed", message: "Your itinerary is ready.", progress: 100, timestamp: "2026-08-03T12:00:01Z", error: null })}\n\n`,
  }));
  await page.route("**/api/trip-jobs/e2e-job-123/result", (route) => route.fulfill({ json: trip, headers: { "X-Trip-Edit-Token": "test-edit-token" } }));
  await page.route("**/api/search/places?*", (route) => route.fulfill({ json: [place] }));
  const stay = {
    id: "stay-jaipur-central",
    city: "Jaipur",
    area: "Central / old city",
    name: "Central / old city stay estimate",
    stay_type: "area_estimate",
    check_in: trip.start_date,
    check_out: trip.end_date,
    nights: 2,
    rooms: 1,
    nightly_price: 3200,
    total_price: 6400,
    currency: "INR",
    amenities: ["Walkable sights"],
    description: "A central planning estimate near the headline sights.",
    booking_url: "https://www.google.com/travel/search?q=Hotels+in+Jaipur",
    maps_url: "https://www.google.com/maps/search/?api=1&query=Jaipur",
    is_fallback: true,
    provenance: { provider: "YatraAI stay planning estimate", status: "estimated", retrieved_at: "2026-08-03T00:00:00Z", expires_at: "2026-08-04T00:00:00Z", confidence: 0.45, source_reference: "app://stay-estimates", disclaimer: "Area-level planning estimate; no reservation is confirmed." },
  };
  const flight = { ...trip.transport_options[0], mode: "flight", provider: "IndiGo fare estimate", code: "6E-204", price: 3600, duration_minutes: 85, departure_city: "Delhi", arrival_city: "Jaipur" };
  await page.route("**/api/stays?*", (route) => route.fulfill({ json: [stay] }));
  await page.route("**/api/transport/flights?*", (route) => route.fulfill({ json: [flight] }));
  await page.route("**/api/trips/e2e-trip-123/stays**", async (route) => {
    if (route.request().method() === "POST") {
      mutableTrip.items = [{ id: "stay-item-1", item_type: "stay", title: stay.name, day_number: null, position: 0, place_id: null, coordinates: null, start_time: null, end_time: null, duration_minutes: null, description: stay.description, notes: "Planning estimate", image_url: null, source_ids: [], provenance: stay.provenance, is_locked: false, metadata: { ...stay, stay_id: stay.id } }];
      return route.fulfill({ json: mutableTrip, headers: { ETag: 'W/"7"' } });
    }
    return route.fulfill({ json: mutableTrip, headers: { ETag: 'W/"8"' } });
  });
  await page.route("**/api/trips/e2e-trip-123/places**", async (route) => {
    const request = route.request();
    if (request.method() === "POST" && request.url().endsWith("/places")) {
      mutableTrip.places = [place];
      return route.fulfill({ json: mutableTrip, headers: { ETag: 'W/"4"' } });
    }
    if (request.method() === "POST" && request.url().includes("/itinerary")) {
      return route.fulfill({ json: mutableTrip, headers: { ETag: 'W/"5"' } });
    }
    if (request.method() === "DELETE") {
      mutableTrip.places = [];
      return route.fulfill({ json: mutableTrip, headers: { ETag: 'W/"6"' } });
    }
    return route.fulfill({ json: mutableTrip });
  });
  await page.route("**/api/trips/e2e-trip-123", (route) => route.fulfill({ json: trip }));

  await page.goto("/");
  await page.locator("#quick-plan-prompt").fill("Plan three heritage days from Delhi to Jaipur for two people.");
  await page.getByRole("button", { name: "Plan this trip" }).click();

  await expect(page.getByRole("heading", { name: "Delhi → Jaipur" })).toBeVisible();
  await expect(page.getByText("Plan conversation")).toBeVisible();
  await expect(page.getByTestId("workspace-shell")).toBeVisible();
  await expect(page.getByRole("button", { name: "Trip overview" })).toBeVisible();
  await expect(page.getByText("Live workspace")).toBeVisible();
  await expect(page.getByText("Day-by-Day Itinerary").first()).toBeVisible();
  await expect(page.getByText("Static reference").first()).toBeVisible();
  await page.getByRole("button", { name: "Saved", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Saved Places/ })).toBeVisible();
  await page.getByRole("button", { name: "Add a place to itinerary" }).click();
  await expect(page.getByTestId("add-to-itinerary-dialog")).toBeVisible();
  await page.getByTestId("place-search-input").fill("palace");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByTestId("place-card-place-city-palace")).toBeVisible();
  await page.getByTestId("save-place-place-city-palace").click();
  await expect(page.getByTestId("save-place-place-city-palace")).toHaveText("Saved");
  await page.getByRole("button", { name: "Close place search" }).click();
  await expect(page.getByText("City Palace").last()).toBeVisible();
  await page.getByRole("button", { name: "Add a place to itinerary" }).click();
  await page.getByRole("tab", { name: "Stay" }).click();
  await expect(page.getByTestId("stay-card-stay-jaipur-central")).toBeVisible();
  await page.getByTestId("add-stay-stay-jaipur-central").click();
  await expect(page.getByTestId("add-stay-stay-jaipur-central")).toHaveText("Added to itinerary");
  await page.getByRole("button", { name: "Close place search" }).click();
  await page.getByRole("button", { name: "Plan", exact: true }).click();
  await expect(page.getByTestId("workspace-shell").getByTestId("trip-commitments")).toBeVisible();
  await expect(page.getByTestId("workspace-shell").getByTestId("stay-commitment")).toContainText(stay.name);
  await expect(page.getByTestId("workspace-shell").getByText(/planning records, not reservations/i)).toBeVisible();
  await page.getByRole("button", { name: "Add a place to itinerary" }).click();
  await page.getByRole("tab", { name: "Flight" }).click();
  await expect(page.getByText("IndiGo fare estimate")).toBeVisible();
  await page.getByRole("button", { name: "Close place search" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Saved", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Saved Places/ })).toBeVisible();
  await page.getByRole("button", { name: "Budget" }).click();
  await expect(page.locator("h3:visible", { hasText: "Budget Breakdown" })).toBeVisible();
  await page.getByRole("button", { name: "Chat" }).click();
  await expect(page.locator('aside[aria-label="Trip conversation and changes"]:visible')).toBeVisible();
  await page.getByRole("button", { name: "Overview" }).click();
  await expect(page.getByRole("heading", { name: "A clear route, one place to adjust it." })).toBeVisible();
  // Framer Motion keeps the button in a short hover transform; force avoids
  // treating that visual transition as an interaction failure.
  await page.locator("#share-trip-btn").click({ force: true });
  await expect(page.locator('input[readonly]')).toHaveValue(/\/trip\/e2e-trip-123$/);

  await page.goto("/trip/e2e-trip-123");
  await expect(page.getByText("Shared Trip")).toBeVisible();
  await expect(page.getByText("Shared itineraries are read-only.")).toBeVisible();
  await expect(page.getByText("Refine itinerary")).toHaveCount(0);
});
