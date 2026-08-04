"""Optional Unsplash destination imagery, cached to keep the UI fast."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.cache.redis_cache import cached
from app.config import settings
from app.models.trip import DataProvenance, DataStatus
from app.services.url_safety import UnsafeUrlError, validate_external_url

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

    retrieved_at = datetime.now(timezone.utc)
    photos = []
    for photo in results:
        urls = photo.get("urls", {})
        user = photo.get("user", {})
        image_url = urls.get("regular")
        if not image_url:
            continue
        try:
            image_url = validate_external_url(
                image_url,
                allowed_hosts={"images.unsplash.com", "plus.unsplash.com"},
            )
        except UnsafeUrlError:
            logger.warning("Discarding an unsafe photo URL returned by Unsplash")
            continue
        photographer_url = user.get("links", {}).get("html")
        if photographer_url:
            try:
                photographer_url = validate_external_url(
                    photographer_url,
                    allowed_hosts={"unsplash.com", "www.unsplash.com"},
                )
            except UnsafeUrlError:
                photographer_url = None
        photos.append({
            "url": image_url,
            "alt": photo.get("alt_description") or f"Travel in {destination}",
            "photographer_name": user.get("name"),
            "photographer_url": photographer_url,
            "provenance": DataProvenance(
                provider="Unsplash",
                status=DataStatus.RECENTLY_VERIFIED,
                retrieved_at=retrieved_at,
                expires_at=retrieved_at + timedelta(days=7),
                confidence=0.8,
                source_reference="https://unsplash.com/",
                disclaimer="Illustrative destination photography; confirm the exact venue and current conditions independently.",
            ).model_dump(mode="json"),
        })
    return photos
