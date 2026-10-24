"""ProviderService — directory lookup + distance ranking (Task 19, Owner: maiabrunne).

Computes great-circle (haversine) distance from the user's location to each
provider and ranks the directory for either a non-emergency suggestion or an
emergency (Req 10.4–10.7):

- Non-emergency: order purely by distance.
- Emergency: cardiac-capable providers first, then by distance.

The user's preferred doctor is flagged in results (Req 10.9). All provider data is
synthetic in the MVP (Req 10.10). Ranking is pure/deterministic for fixed inputs.

Builds on the Task 18 data layer: reads ``Provider`` dataclasses from
``care_repository`` (which manages its own connections), so this service takes no
connection handle.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..db import care_repository as repo
from ..db.care_models import Provider

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometres."""
    r_lat1, r_lat2 = math.radians(lat1), math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(d_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class ProviderSuggestion:
    """A ranked provider plus its distance and preferred flag."""

    provider: Provider
    distance_km: float
    is_preferred: bool


class ProviderService:
    """Ranks the seeded provider directory relative to a location."""

    def suggest(
        self,
        lat: float,
        lon: float,
        *,
        emergency: bool = False,
        preferred_id: int | None = None,
    ) -> list[ProviderSuggestion]:
        """Return provider suggestions ranked by suitability.

        Distance is rounded to 2 dp for display stability. Ranking is deterministic:
        ties break by provider id so repeated calls return identical order (Req 10.7).
        """
        suggestions: list[ProviderSuggestion] = []
        for p in repo.list_providers():
            distance = round(haversine_km(lat, lon, p.lat, p.lon), 2)
            suggestions.append(
                ProviderSuggestion(
                    provider=p,
                    distance_km=distance,
                    is_preferred=preferred_id is not None and p.id == preferred_id,
                )
            )

        if emergency:
            # Cardiac-capable first (0 sorts before 1), then nearest, then id.
            suggestions.sort(
                key=lambda s: (
                    0 if s.provider.can_handle_cardiac_emergency else 1,
                    s.distance_km,
                    s.provider.id or 0,
                )
            )
        else:
            suggestions.sort(key=lambda s: (s.distance_km, s.provider.id or 0))

        return suggestions
