"""Annotate corpus files with geocoding ground truth from Nominatim.

Reads each NER corpus file, queries Nominatim (OpenStreetMap) for each
named entity, and adds ``expected_geocoded_locations`` and
``expected_event_location`` fields.

Usage:
    uv run python scripts/annotate_geocoding.py

"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "LocationExtractionService/1.0 (evaluation-annotation-script)"
REQUEST_DELAY = 1.1

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(BASE_DIR, "tests", "corpus")

CORPUS_FILES = [
    "en_simple.json",
    "en_paragraphs.json",
    "en_edge_cases.json",
    "fr_simple.json",
    "fr_paragraphs.json",
    "fr_edge_cases.json",
]

_cache: dict[str, dict | None] = {}


def _is_named_entity(text: str) -> bool:
    """Return True if *text* looks like a proper named entity (starts with uppercase)."""
    return bool(text and text[0].isupper())


def _query_nominatim(text: str) -> dict | None:
    """Query Nominatim for *text* and return ``{lat, lon, country}`` or ``None``."""
    if text in _cache:
        return _cache[text]

    params = urllib.parse.urlencode({"q": text, "format": "json", "limit": 1, "addressdetails": 1})
    url = f"{NOMINATIM_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data:
                result = data[0]
                lat = float(result["lat"])
                lon = float(result["lon"])
                address = result.get("address") or {}
                country_code = (address.get("country_code") or "").upper() or None
                entry = {"lat": lat, "lon": lon, "country": country_code}
                _cache[text] = entry
                return entry
    except Exception as exc:
        print(f"    [WARN] Nominatim query failed for '{text}': {exc}", file=sys.stderr)

    _cache[text] = None
    return None


def _resolve_event_location(sample: dict, geo_by_text: dict[str, dict]) -> dict | None:
    """Determine expected event location for a sample.

    Heuristic: first GPE entity with a geocoded result; else first resolved
    entity; else ``None``.

    """
    for entity in sample["entities"]:
        text = entity["text"]
        if entity["label"] == "GPE" and text in geo_by_text:
            return {"text": text, "country": geo_by_text[text]["country"]}
    for entity in sample["entities"]:
        text = entity["text"]
        if text in geo_by_text:
            return {"text": text, "country": geo_by_text[text]["country"]}
    return None


def _process_file(filepath: str) -> int:
    """Annotate a single corpus file.  Returns number of samples annotated."""
    with open(filepath) as f:
        corpus = json.load(f)

    annotated = 0
    for sample in corpus["samples"]:
        if "expected_geocoded_locations" in sample:
            continue

        geo_locations: list[dict] = []
        geo_by_text: dict[str, dict] = {}

        for entity in sample["entities"]:
            text = entity["text"]
            if not _is_named_entity(text):
                continue
            if text in geo_by_text:
                continue

            result = _query_nominatim(text)
            if result:
                entry = {
                    "text": text,
                    "lat": result["lat"],
                    "lon": result["lon"],
                    "country": result["country"],
                }
                geo_locations.append(entry)
                geo_by_text[text] = entry

            time.sleep(REQUEST_DELAY)

        sample["expected_geocoded_locations"] = geo_locations
        sample["expected_event_location"] = _resolve_event_location(sample, geo_by_text)
        annotated += 1

    with open(filepath, "w") as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return annotated


def main() -> None:
    """Annotate all corpus files with geocoding ground truth."""
    for name in CORPUS_FILES:
        path = os.path.join(CORPUS_DIR, name)
        if not os.path.exists(path):
            print(f"  [SKIP] {name} (not found)")
            continue
        print(f"  Processing {name} ...")
        count = _process_file(path)
        print(f"    Annotated {count} samples ({len(_cache)} cached queries)")


if __name__ == "__main__":
    main()
