# ADR-008: Geocoding Evaluation Corpus and Decoupled Metrics

## Status

Accepted

## Date

2026-05-15

## Context

ADR-002 established NER quality evaluation (Stages 1-2) with entity-level exact-match metrics and a corpus of annotated test cases. However, geocoding quality (Stages 3-4 — toponym resolution and event location inference) had no evaluation data or metrics.

The existing corpus files only contained NER annotations (`text`, `label`, `start`, `end`). The evaluation code in `src/evaluation/` had skeleton functions for geocoding evaluation (`evaluate_geocoding()`, `evaluate_geocoding_corpus()`) but:

1. No corpus files included `expected_geocoded_locations` or `expected_event_location` fields
2. No coordinate-accuracy metrics existed — only geocoding rate and country accuracy
3. The `--geocoding` CLI flag ran the full pipeline (NER → geocoding), conflating NER errors with geocoding errors
4. Running `uv run python -m src.evaluation --geocoding` produced empty/no useful results

## Decision

### 1. Extend Existing Corpus Files with Geocoding Annotations

Add `expected_geocoded_locations` (list of `{text, lat, lon, country}`) and `expected_event_location` (`{text, country}` or `null`) to every sample in all 6 existing corpus files. These fields are optional — NER evaluation ignores them entirely, and geocoding evaluation only reads them when present.

Ground truth coordinates were sourced from the [Nominatim](https://nominatim.openstreetmap.org/) API (OpenStreetMap) with `addressdetails=1` to obtain country codes. A one-time annotation script (`scripts/annotate_geocoding.py`) handles the lookup and caches results.

Non-named entities (lowercase common nouns like "river" mis-tagged as LOC) are excluded from geocoding annotations.

### 2. Add Coordinate-Distance Metrics

The `evaluate_geocoding()` function now also computes:

| Metric               | Definition                                                                        |
| -------------------- | --------------------------------------------------------------------------------- |
| `mean_distance_km`   | Mean great-circle (Haversine) distance between predicted and expected coordinates |
| `within_1km`         | Fraction of resolved entities within 1km of expected                              |
| `within_10km`        | Fraction within 10km                                                              |
| `within_100km`       | Fraction within 100km                                                             |
| `distance_checkable` | Count of pairs with both predicted and expected coordinates                       |

These are only computed when both predicted and expected entries include `lat`/`lon`. Entries where geocoding returned `None` contribute to the geocoding rate denominator but not to distance metrics.

### 3. Decouple Geocoding Evaluation from NER

A new `run_geocoding_pipeline_on_corpus()` function feeds the ground-truth `entities` from the corpus directly into `GeoPipeline`, bypassing `NerPipeline`. This ensures geocoding quality is measured independently of NER quality.

The decoupled functions are:

- `run_geocoding_pipeline_on_corpus()` — bypasses NER, feeds corpus entities to GeoPipeline + DisambiguatePipeline
- `evaluate_geocoding_decoupled_corpus()` — wraps above with metrics
- `evaluate_geocoding_decoupled_all_corpora()` — aggregate across all corpora

### 4. Update CLI with Explicit Flags

The `--geocoding` flag now uses the decoupled evaluation. A new `--ner` flag runs NER-only evaluation. Without flags, both modes run sequentially.

| Command                                       | Mode                  |
| --------------------------------------------- | --------------------- |
| `uv run python -m src.evaluation`             | Full: NER + Geocoding |
| `uv run python -m src.evaluation --ner`       | NER only              |
| `uv run python -m src.evaluation --geocoding` | Geocoding only        |

The old full-pipeline `evaluate_geocoding_corpus()` function is kept but can be accessed via the class directly if needed for comparison.

## Consequences

### Positive

- One corpus file serves both NER and geocoding evaluation
- Geocoding metrics are no longer contaminated by NER errors
- Coordinate-distance metrics provide granular quality signal beyond binary country-match
- CLI is explicit about which evaluation mode is running
- All existing NER evaluation is completely unaffected

### Negative

- Auto-annotation via Nominatim introduces ground-truth noise for ambiguous place names (e.g., "Athens" → Athens, Georgia instead of Athens, Greece). These cases must be manually corrected.
- Event location annotation uses a simple heuristic (first resolved GPE), which is wrong for some samples
- ~213 unique Nominatim queries required for initial annotation (~4 minutes with rate limiting)

### Neutral

- The `--geocoding` CLI flag now means something different from before (decoupled instead of full-pipeline)
- Annotation script must be run with internet access to Nominatim

## Related Documents

- [Evaluation Guide](../evaluation.md)
- [ADR-002: NER Evaluation Protocol](ADR-002-ner-evaluation-protocol.md)
- [Architecture: Location Extraction](../architecture/location-extraction.md)
