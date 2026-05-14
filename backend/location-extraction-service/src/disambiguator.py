"""Stage 4: Event location inference (disambiguation)."""

import re
from dataclasses import dataclass, field

import pycountry

_BOOST_PREPOSITIONS = frozenset({"in", "at", "near"})
_PREPOSITION_BOOST = 1.3


@dataclass
class DisambiguateResult:
    """Result of running Stage 4 (event location inference).

    Attributes:
        event_location: The best-guess event location with coordinates and
            confidence, or None if no location could be determined.
        all_locations: All scored locations with their attributes.

    """

    event_location: dict | None = None
    all_locations: list[dict] = field(default_factory=list)


def _country_name(code: str) -> str:
    country = pycountry.countries.get(alpha_2=code)
    return country.name if country else code


def _preposition_boost(loc_text: str, text: str) -> float:
    """Return boost multiplier if a boost preposition precedes loc_text in text."""
    text_lower = text.lower()
    loc_lower = loc_text.lower()
    pos = text_lower.find(loc_lower)
    if pos <= 0:
        return 1.0

    before = text_lower[:pos].rstrip()
    if not before:
        return 1.0

    words = before.split()
    if not words:
        return 1.0

    prev_word = re.sub(r"[^a-z]", "", words[-1])
    return _PREPOSITION_BOOST if prev_word in _BOOST_PREPOSITIONS else 1.0


class DisambiguatePipeline:
    """Infers the primary event location from a list of geocoded locations.

    Uses position, entity type, and preposition context to score and rank
    locations. This is Stage 4 of the location extraction pipeline.
    """

    def run(self, locations: list[dict], text: str) -> DisambiguateResult:
        """Score locations and return the best-guess event location.

        Args:
            locations: Geocoded location dicts with text, lat, lon, country.
            text: Original input text for preposition context analysis.

        Returns:
            DisambiguateResult with the best event location and all scored
            locations.

        """
        geocoded = [loc for loc in locations if "lat" in loc and "lon" in loc]
        if not geocoded:
            return DisambiguateResult()

        scored = []
        for i, loc in enumerate(geocoded):
            position_score = 1.0 / (i + 1)
            type_multiplier = 2.5 if loc.get("type") == "GPE" else 1.0
            boost = _preposition_boost(loc["text"], text)
            final_score = position_score * type_multiplier * boost

            scored.append(
                {
                    "text": loc["text"],
                    "lat": loc["lat"],
                    "lon": loc["lon"],
                    "country": loc["country"],
                    "country_name": _country_name(loc["country"]),
                    "type": loc.get("type"),
                    "score": final_score,
                }
            )

        best = max(scored, key=lambda x: x["score"])
        return DisambiguateResult(
            event_location={
                "text": best["text"],
                "lat": best["lat"],
                "lon": best["lon"],
                "country": best["country"],
                "country_name": best["country_name"],
                "confidence": min(best["score"] * 0.5, 1.0),
            },
            all_locations=scored,
        )
