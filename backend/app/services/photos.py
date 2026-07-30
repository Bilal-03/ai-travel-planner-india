"""Optional Unsplash destination imagery, cached to keep the UI fast."""

import logging
from typing import Optional

import httpx

from app.cache.redis_cache import cached
from app.config import settings

logger = logging.getLogger(__name__)


@cached("destination_photos", ttl_seconds=86400 * 7)
async def get_destination_photos(destination: str, limit: int = 3) -> list[dict]:
    """Fetch landscape destination photos when an Unsplash key is configured."""
    if not settings.unsplash_access_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(
                "https://api.unsplash.com/search/photos",
                params={"query": f"{destination} India travel", "per_page": limit, "orientation": "landscape"},
                headers={"Authorization": f"Client-ID {settings.unsplash_access_key}"},
            )
            response.raise_for_status()
            results = response.json().get("results", [])
    except Exception as error:
        logger.warning("Unsplash search failed for %s: %s", destination, error)
        return []

    photos = []
    for photo in results:
        urls = photo.get("urls", {})
        user = photo.get("user", {})
        image_url = urls.get("regular")
        if not image_url:
            continue
        photos.append({
            "url": image_url,
            "alt": photo.get("alt_description") or f"Travel in {destination}",
            "photographer_name": user.get("name"),
            "photographer_url": user.get("links", {}).get("html"),
        })
    return photos
