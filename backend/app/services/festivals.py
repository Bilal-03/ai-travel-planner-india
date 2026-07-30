"""Small, auditable India festival calendar used to enrich trip plans offline."""

from datetime import date


# Fixed-date celebrations are generated for every trip year. Lunar dates are
# intentionally included only where verified, rather than guessed.
FIXED_FESTIVALS = [
    ("Pongal", 1, 14, 4, {"tamil nadu", "chennai", "madurai", "coimbatore", "kodaikanal"}, "Harvest celebrations, temple rituals, and busy local transport.", "Book intercity travel early and expect altered shop hours."),
    ("Republic Day", 1, 26, 1, {"delhi"}, "National celebrations and the Republic Day Parade in Delhi.", "Expect road closures and secure tickets well in advance."),
    ("Independence Day", 8, 15, 1, {"delhi"}, "National celebrations centred on the Red Fort.", "Allow extra time for security and traffic diversions."),
    ("Christmas", 12, 25, 2, {"goa", "kochi", "pondicherry"}, "Festive services, markets, and a lively high season.", "Reserve stays early; prices and demand rise sharply."),
]

VERIFIED_2026_FESTIVALS = [
    ("Holi", date(2026, 3, 4), date(2026, 3, 4), {"agra", "delhi", "jaipur", "mathura", "varanasi"}, "India's festival of colours brings energetic public celebrations.", "Wear clothes you can stain, protect electronics, and confirm venue rules."),
    ("Ugadi / Gudi Padwa", date(2026, 3, 19), date(2026, 3, 19), {"bengaluru", "hyderabad", "mumbai", "pune"}, "New-year celebrations with temple visits and special meals.", "Expect busier temples and some businesses to run shorter hours."),
    ("Onam", date(2026, 8, 26), date(2026, 8, 26), {"kochi", "munnar", "alappuzha", "varkala", "thiruvananthapuram", "wayanad"}, "Kerala's harvest festival features floral displays and traditional feasts.", "Book trains and houseboats early; ask for an Onam sadya in advance."),
    ("Diwali", date(2026, 11, 8), date(2026, 11, 11), {"all"}, "The festival of lights brings decorated streets, family gatherings, and high demand.", "Book early, expect traffic, and check local firework restrictions."),
]


def get_festivals_for_trip(destination: str, start_date: date, end_date: date) -> list[dict]:
    destination_key = destination.casefold().strip()
    events: list[dict] = []

    for name, month, day, duration, places, description, tip in FIXED_FESTIVALS:
        if destination_key not in places:
            continue
        event_start = date(start_date.year, month, day)
        event_end = date(start_date.year, month, day + duration - 1)
        if event_start <= end_date and event_end >= start_date:
            events.append({"name": name, "start_date": event_start, "end_date": event_end, "description": description, "travel_tip": tip})

    if start_date.year == 2026:
        for name, event_start, event_end, places, description, tip in VERIFIED_2026_FESTIVALS:
            if destination_key in places or "all" in places:
                if event_start <= end_date and event_end >= start_date:
                    events.append({"name": name, "start_date": event_start, "end_date": event_end, "description": description, "travel_tip": tip})
    return events
