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
    vibes: ["culture"],
    accommodation_preference: "budget",
    adults: 2,
    children: 0,
    travel_preference: "balanced",
    pace: "balanced",
    dietary_preference: null,
    senior_citizens: 0,
    accessibility_requirements: null,
    allow_early_morning_travel: false,
    allow_late_night_travel: false,
    transport_options: [train],
    selected_transport: train,
    day_plans: [{
      day_number: 1,
      date: start,
      weather: null,
      transport: null,
      activities: [{ poi: { id: "amber", name: "Amber Fort", category: "fort", coordinates: { lat: 26.9855, lng: 75.8513 }, estimated_visit_minutes: 120, estimated_cost: 500, description: null, opening_hours: "09:00-17:00" }, start_time: "10:00", end_time: "12:00", estimated_cost: 500, notes: null, is_backup: false }],
      meals: [{ name: "Suggested meal type: Rajasthani thali", cuisine: "Rajasthani", meal_type: "lunch", estimated_cost: 300, notes: "Choose a trusted local restaurant." }],
      backup_activities: [],
      day_budget: 1200,
      day_spent: 800,
      local_transport_minutes: 30,
      local_transport_cost: 120,
      notes: "Explore Amber Fort.",
    }],
    budget: { outbound_transport: 1800, return_transport: 1800, transport: 3600, food: 600, activities: 1000, accommodation: 2400, local_transport: 500, taxes_buffer: 405, miscellaneous: 0, total_estimated: 8505, remaining: 1495 },
    route_segments: [],
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
  await page.route("**/health", (route) => route.fulfill({ json: { status: "healthy", services: {} } }));
  await page.route("**/api/search/cities?*", (route) => {
    const city = new URL(route.request().url()).searchParams.get("q")?.toLowerCase() || "";
    const result = city.includes("jaipur")
      ? { name: "Jaipur", state: "Rajasthan", display_name: "Jaipur, Rajasthan", coordinates: { lat: 26.9124, lng: 75.7873 } }
      : { name: "Delhi", state: "Delhi", display_name: "Delhi, Delhi", coordinates: { lat: 28.6139, lng: 77.209 } };
    return route.fulfill({ json: [result] });
  });
  await page.route("**/api/trips/progress/**", (route) => route.fulfill({ status: 204 }));
  await page.route("**/api/trips/generate", (route) => route.fulfill({ json: trip, headers: { "X-Trip-Edit-Token": "test-edit-token" } }));
  await page.route("**/api/trips/e2e-trip-123", (route) => route.fulfill({ json: trip }));

  await page.goto("/");
  await page.locator("#origin-city").fill("Delhi");
  await page.getByRole("button", { name: "Delhi" }).click();
  await page.locator("#destination-city").fill("Jaipur");
  await page.getByRole("button", { name: "Jaipur" }).click();
  await page.locator("#start-date").fill(trip.start_date);
  await page.locator("#end-date").fill(trip.end_date);
  await page.locator("#generate-trip-btn").click();

  await expect(page.getByRole("heading", { name: "Delhi → Jaipur" })).toBeVisible();
  // Framer Motion keeps the button in a short hover transform; force avoids
  // treating that visual transition as an interaction failure.
  await page.locator("#share-trip-btn").click({ force: true });
  await expect(page.locator('input[readonly][value$="/trip/e2e-trip-123"]')).toBeVisible();

  await page.goto("/trip/e2e-trip-123");
  await expect(page.getByText("Shared Trip")).toBeVisible();
  await expect(page.getByText("Shared itineraries are read-only.")).toBeVisible();
  await expect(page.getByText("Refine itinerary")).toHaveCount(0);
});
