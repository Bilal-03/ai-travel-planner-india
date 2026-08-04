import { expect, test } from "@playwright/test";

function city(name: string) {
  return { name, state: null, coordinates: { lat: 26, lng: 75 }, iata_code: null, station_code: null };
}

function multiCityTrip(order = ["Jaipur", "Jodhpur", "Udaipur"]) {
  const origin = city("Delhi");
  const stays = order.map((name, index) => ({
    id: `stay-${name.toLowerCase()}`,
    city: city(name),
    position: index,
    arrival_date: `2026-09-${String(10 + index * 2).padStart(2, "0")}`,
    departure_date: `2026-09-${String(12 + index * 2).padStart(2, "0")}`,
    nights: index === 2 ? 3 : 2,
    notes: null,
  }));
  const legs = [
    ["Delhi", order[0]],
    [order[0], order[1]],
    [order[1], order[2]],
    [order[2], "Delhi"],
  ].map(([from, to], index) => ({
    id: `leg-${index}`,
    origin: city(from),
    destination: city(to),
    date: `2026-09-${String(10 + index * 2).padStart(2, "0")}`,
    mode: "train",
    selected_offer: null,
    alternatives: [],
    duration_minutes: 240,
    fare: 900,
    origin_stay_id: null,
    destination_stay_id: null,
  }));
  return {
    id: "multi-trip-123",
    origin,
    destination_stays: stays,
    travel_legs: legs,
    itinerary_days: [{ day_number: 1, date: "2026-09-10", stay_id: stays[0].id, destination: stays[0].city, weather: null, visits: [], meals: [], travel_leg_id: legs[0].id, day_budget: 1200, day_spent: 0, notes: null }],
    visits: [],
    transport_selections: [],
    start_date: "2026-09-10",
    end_date: "2026-09-18",
    total_days: 9,
    vibes: ["culture"],
    adults: 2,
    children: 0,
    travel_preference: "balanced",
    pace: "balanced",
    dietary_preference: null,
    senior_citizens: 0,
    accessibility_requirements: null,
    budget: { outbound_transport: 900, return_transport: 900, transport: 3600, food: 7200, activities: 0, local_transport: 2700, taxes_buffer: 675, miscellaneous: 0, total_estimated: 14175, remaining: 15825 },
    generation_notes: [],
    created_at: "2026-08-04T00:00:00Z",
  };
}

test("generates and reorders a multi-city route without leaving the route studio", async ({ page }) => {
  const initial = multiCityTrip();
  await page.route("**/api/multi-city/generate", (route) => route.fulfill({ json: initial, headers: { "X-Trip-Edit-Token": "multi-edit-token" } }));
  await page.route("**/api/multi-city/multi-trip-123/reorder", (route) => route.fulfill({ json: multiCityTrip(["Jaipur", "Udaipur", "Jodhpur"]) }));

  await page.goto("/");
  await page.getByRole("button", { name: "Generate multi-city route" }).click();
  await expect(page.getByRole("heading", { name: "Delhi → Jaipur → Jodhpur → Udaipur → Delhi" })).toBeVisible();
  await page.getByRole("button", { name: "Move Udaipur up" }).click();
  await expect(page.getByRole("heading", { name: "Delhi → Jaipur → Udaipur → Jodhpur → Delhi" })).toBeVisible();
});
