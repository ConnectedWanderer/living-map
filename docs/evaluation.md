# Evaluation Guide

## Overview

The location extraction service provides **two evaluation modes**, both using the same corpus files in `backend/location-extraction-service/tests/corpus/`:

| Mode                       | Stages                                    | Measures                                                                       | Use Case                                            |
| -------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------- |
| **NER** (Stages 1-2)       | Language detection + spaCy NER            | Precision, Recall, F1 for entity extraction                                    | Is the NER finding the right locations?             |
| **Geocoding** (Stages 3-4) | geonamescache resolution + disambiguation | Geocoding rate, country accuracy, coordinate distance, event location accuracy | Is the geocoder resolving to the right coordinates? |

Geocoding evaluation is **decoupled from NER** — it uses the ground-truth `entities` from the corpus as input, so geocoding quality is measured independently of NER quality.

## CLI Commands

```bash
# Full evaluation (NER + Geocoding) on all corpora
uv run python -m src.evaluation

# Single mode on all corpora
uv run python -m src.evaluation --ner
uv run python -m src.evaluation --geocoding

# Single corpus
uv run python -m src.evaluation tests/corpus/en_simple.json
uv run python -m src.evaluation --ner tests/corpus/en_simple.json
uv run python -m src.evaluation --geocoding tests/corpus/en_simple.json

# Large-scale corpus generation (on-demand, lazy)
uv run convert-en-wikiann
uv run convert-wikiner-fr
```

### CLI Flags

| Flags               | Behavior                               |
| ------------------- | -------------------------------------- |
| _(no flags)_        | Runs both NER and Geocoding evaluation |
| `--ner`             | NER evaluation only                    |
| `--geocoding`       | Geocoding evaluation only (decoupled)  |
| `--ner --geocoding` | Both, overrides the default            |

> **Note**: The `--geocoding` flag replaces the old `--geocoding` behavior from the full-pipeline evaluation. Geocoding is now always evaluated decoupled from NER to give independent quality signal.

## NER Evaluation

### How It Works

1. For each corpus sample, runs the full NER pipeline (language detection → spaCy NER)
2. Compares predicted entities against the corpus annotations
3. Uses **entity-level exact match** — a prediction is correct only when `text`, `start`, `end`, and `label` all match exactly (CoNLL-style)
4. No partial credit

### Metrics

| Metric        | Formula             | What It Tells You                       |
| ------------- | ------------------- | --------------------------------------- |
| **Precision** | TP / (TP + FP)      | How many of our predictions are correct |
| **Recall**    | TP / (TP + FN)      | How many actual entities we found       |
| **F1**        | 2 × P × R / (P + R) | Balanced quality score                  |

Metrics are computed **overall** (across all entity types) and **per-type** (GPE vs LOC).

### Example Output

```
Corpora: 6  Total samples: 138

Aggregate Metrics (entity-level):
  Precision: 54.0%
  Recall:    46.5%
  F1:        50.0%
  TP: 181  FP: 154  FN: 208

Per-type:
  GPE:  Precision: 93.8%  Recall: 43.0%  F1: 59.0%
  LOC:  Precision: 29.5%  Recall: 55.5%  F1: 38.5%

Per-Corpus Summary:
  en_simple.json         45 samples    P=93.2%  R=76.4%  F1=84.0%
  en_paragraphs.json     15 samples    P=83.8%  R=67.0%  F1=74.4%
  fr_simple.json         43 samples    P=22.5%  R=20.9%  F1=21.7%
```

> **Tip**: The low recall on GPE is expected because the corpus includes country names that spaCy's small model often misses. Low precision on LOC is expected because spaCy tags many common nouns (e.g., "river", "city") as LOC even though they aren't proper place names.

## Geocoding Evaluation

### How It Works

1. For each corpus sample, takes the ground-truth `entities` (bypasses NER)
2. Feeds them to `GeoPipeline` (geonamescache) for coordinate resolution
3. Feeds resolved locations + original text to `DisambiguatePipeline` for event location inference
4. Compares results against `expected_geocoded_locations` and `expected_event_location`

### Metrics

| Metric                        | Definition                                                                                     |
| ----------------------------- | ---------------------------------------------------------------------------------------------- |
| **Geocoding Rate**            | % of expected places that were successfully resolved                                           |
| **Country Accuracy**          | % of resolved places with correct country code                                                 |
| **Mean Distance**             | Mean great-circle distance (Haversine) in km between predicted and expected coordinates        |
| **Within 1km / 10km / 100km** | % of resolved places whose coordinates fall within the given distance of the expected location |
| **Event Location Accuracy**   | % of samples where the predicted event location (text + country) matches expected              |

### Example Output

```
Corpora: 6  Total samples: 138

Aggregate Geocoding Metrics:
  Geocoding Rate:    62.0%
  Country Accuracy:  77.3%
  Expected: 376  Geocoded: 233  Country Matches: 180
  Mean Distance:     1626.2 km
  Within 1km:        36.1%
  Within 10km:       70.8%
  Within 100km:      73.4%
  Distance Checkable: 233

Aggregate Event Location Metrics:
  Accuracy: 64.1%
  Correct: 82 / 128

Per-Corpus Summary:
  en_simple.json         45 samples  Geo=73.0%  Ctry=75.4%  Dist=1684.0km  10km=73.8%  Event=64.4%
  en_paragraphs.json     15 samples  Geo=60.6%  Ctry=65.0%  Dist=2849.5km  10km=55.0%  Event=53.3%
```

The per-sample view shows detailed resolution for each sample:

```
  1. The meeting in Paris was attended by officials from London.
       Predicted geocoded: 2 locations
       Expected geocoded:  2 locations
       Predicted event: Paris (FR, conf=1.00)
       Expected event:  Paris (FR)
```

## Corpus Format

All corpus files live in `tests/corpus/` as JSON with this schema:

```json
{
  "samples": [
    {
      "text": "The meeting in Paris was attended by officials from London.",
      "language": "en",
      "entities": [
        { "text": "Paris", "label": "GPE", "start": 15, "end": 20 },
        { "text": "London", "label": "GPE", "start": 52, "end": 58 }
      ],
      "expected_geocoded_locations": [
        { "text": "Paris", "lat": 48.8535, "lon": 2.3484, "country": "FR" },
        { "text": "London", "lat": 51.5074, "lon": -0.1278, "country": "GB" }
      ],
      "expected_event_location": { "text": "Paris", "country": "FR" }
    }
  ]
}
```

### Field Guide

| Field                         | Required for NER | Required for Geo | Description                                 |
| ----------------------------- | ---------------- | ---------------- | ------------------------------------------- |
| `text`                        | Yes              | Yes              | The input text                              |
| `language`                    | Yes              | Yes              | Expected language code                      |
| `entities`                    | Yes              | Yes              | NER entities with character offsets         |
| `expected_geocoded_locations` | No               | Yes              | Expected geocoding results with coordinates |
| `expected_event_location`     | No               | Yes              | Expected primary event location             |

Non-named entities (common nouns like "river" mis-tagged as LOC) should **not** be included in `expected_geocoded_locations`.

### Available Corpora

> Large-scale corpora (`en_wikiann.json`, `fr_wikiner_gold.json`) are **not committed** to git. They are generated lazily on first `uv run python -m src.evaluation` when the `datasets` library is available — or explicitly via `uv run convert-en-wikiann` / `uv run convert-wikiner-fr`. Hand-written corpora always work without any setup.

| File                        | Language | Focus                                     | NER Samples | Geo Entities |
| --------------------------- | -------- | ----------------------------------------- | ----------- | ------------ |
| `en_simple.json`            | EN       | Simple sentences, 1-2 locations           | 45          | ~89          |
| `en_paragraphs.json`        | EN       | News paragraphs, 3-5 locations            | 15          | ~99          |
| `en_edge_cases.json`        | EN       | Empty text, no locations, edge cases      | 10          | ~16          |
| `fr_simple.json`            | FR       | Simple sentences                          | 43          | ~84          |
| `fr_paragraphs.json`        | FR       | News paragraphs                           | 15          | ~90          |
| `fr_edge_cases.json`        | FR       | Edge cases                                | 10          | ~8           |
| `en_wikiann.json` †         | EN       | WikiANN — Wikipedia (7K LOC samples)      | ~7K         | —            |
| `fr_wikiner_gold.json` †    | FR       | WikiNER-fr-gold — Wikipedia (3.8K samples)| ~3.8K       | —            |

† _NER only — no geocoding annotations. Generated on demand._

## Adding New Test Cases

### NER-only Sample

```json
{
  "text": "The summit in Nairobi attracted delegates from across Africa.",
  "language": "en",
  "entities": [
    { "text": "Nairobi", "label": "GPE", "start": 14, "end": 21 },
    { "text": "Africa", "label": "LOC", "start": 58, "end": 64 }
  ]
}
```

### Adding Geocoding Annotations

To add geocoding annotations to an existing or new sample:

1. **Look up coordinates** via [Nominatim](https://nominatim.openstreetmap.org/):

   ```bash
   curl "https://nominatim.openstreetmap.org/search?q=Nairobi&format=json&limit=1&addressdetails=1"
   ```

   Extract `lat`, `lon`, and `address.country_code` from the first result.
   Always use `addressdetails=1` to get the full address.

2. **Add to the sample**:

   ```json
   "expected_geocoded_locations": [
     {"text": "Nairobi", "lat": -1.2921, "lon": 36.8219, "country": "KE"},
     {"text": "Africa", "lat": -8.7832, "lon": 34.5085, "country": null}
   ],
   "expected_event_location": {"text": "Nairobi", "country": "KE"}
   ```

3. **Verify character offsets** by running the offset checker:
   ```bash
   uv run python scripts/fix_corpus_offsets.py --check
   ```

### Best Practices

- Use `addressdetails=1` when querying Nominatim to get country codes
- For ambiguous names (e.g., "Paris", "Athens"), verify the Nominatim result is the intended location — the first result is not always contextually correct
- Natural features (rivers, mountains, regions) may not have a meaningful country code — set to `null` if unavailable
- Non-named entities (lowercase, common nouns) should be excluded from `expected_geocoded_locations`
- Event location should reflect the primary subject location, not necessarily the first entity in the text

## Interpreting Results

### Good Signs

| Metric                 | Threshold                    | What It Means                               |
| ---------------------- | ---------------------------- | ------------------------------------------- |
| NER F1 > 80%           | On `_simple` corpora         | Pipeline is working well for standard cases |
| Geocoding Rate > 80%   | On GPE entities              | Most cities/countries are being resolved    |
| Country Accuracy > 95% | On GPE entities              | Cities are resolving to the correct country |
| Within 10km > 90%      | On city entities             | Coordinates are precise                     |
| Event Accuracy > 80%   | On samples with clear events | Disambiguation is working                   |

### Concerning Signs

- **Low Geocoding Rate on GPE entities**: geonamescache is missing known cities — check population threshold or index
- **Low Country Accuracy**: Ambiguous names are resolving to the wrong country (e.g., "Paris" → US)
- **High Mean Distance combined with low Within 1%**: Systematic resolution to wrong locations
- **Low Event Accuracy**: The disambiguation heuristic (first GPE) is wrong for many samples — may need context-aware scoring

### Common Failure Modes

- **"Cairo" → Egypt, US** (geonamescache resolves to Cairo, Illinois)
- **"Athens" → Athens, Georgia** instead of Athens, Greece
- **Rivers/mountains** → Not resolved (out of scope for geonamescache's city-only data)
- **Continents/regions** → Unexpected resolutions ("Africa" → Tunisia, "Asia" → Philippines)
- **Event location = first GPE** → Wrong when the primary subject is not the first mentioned city

## Re-annotating Corpora

The `scripts/annotate_geocoding.py` script can be re-run if needed:

```bash
uv run python scripts/annotate_geocoding.py
```

It queries Nominatim for each named entity with `addressdetails=1`, caches results, and auto-determines event locations via a heuristic (first resolved GPE). After running, review the output for ambiguous names and fix any incorrect annotations manually.

## Related Documents

- [Architecture: Location Extraction](architecture/location-extraction.md)
- [ADR-002: NER Evaluation Protocol](decisions/ADR-002-ner-evaluation-protocol.md)
- [ADR-008: Geocoding Evaluation Corpus](decisions/ADR-008-geocoding-evaluation-corpus.md)
