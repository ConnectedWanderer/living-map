# ADR-002: NER Quality Evaluation Protocol

## Status

Accepted

## Date

2026-05-13

## Context

The location extraction service needs a standardized way to measure and track the quality of its NER pipeline (Stages 1-2: language detection + entity extraction). Without objective metrics, we cannot:

- Know whether changes improve or regress quality
- Compare spaCy model variants (e.g., small vs. large)
- Set meaningful quality gates in CI/CD
- Detect regressions when adding new languages

### Scope

This ADR covers evaluation of **Stages 1-2 only**:

- **Stage 1**: Language detection (`detector.py`)
- **Stage 2**: NER entity extraction (`extractor.py`)

Geocoding (Stage 3) and event location inference (Stage 4) will be addressed in a future ADR.

### Considered Evaluation Approaches

| Approach                     | Granularity  | Complexity | Relevance to Downstream                   |
| ---------------------------- | ------------ | ---------- | ----------------------------------------- |
| **Entity-level exact match** | Whole-entity | Low        | High — geocoding depends on correct spans |
| Token-level BIO tagging      | Per-token    | Medium     | Medium — measures token classification    |
| Relaxed (partial overlap)    | Whole-entity | Medium     | Low — downstream needs exact coordinates  |
| Text-based (string match)    | Surface form | Low        | Low — ignores span boundaries             |

## Decision

**Chosen: Entity-level exact match evaluation**

### What This Means

A predicted entity is counted as **correct (True Positive)** only if **all four** fields match the expected annotation exactly:

| Field   | Criterion                         |
| ------- | --------------------------------- |
| `text`  | Character-for-character identical |
| `start` | Character offset matches exactly  |
| `end`   | Character offset matches exactly  |
| `label` | Entity type matches (GPE or LOC)  |

No partial credit is awarded. This is the strictest evaluation mode (consistent with CoNLL-2003).

### Metrics Computed

| Metric        | Formula             | What It Tells Us                        |
| ------------- | ------------------- | --------------------------------------- |
| **Precision** | TP / (TP + FP)      | How many of our predictions are correct |
| **Recall**    | TP / (TP + FN)      | How many actual entities we found       |
| **Entity F1** | 2 × P × R / (P + R) | Balanced quality score                  |

Each metric is computed:

- **Overall** across all entity types
- **Per type** (GPE, LOC) separately

### Why Not Other Approaches

| Approach            | Reason for Rejection                                                                         |
| ------------------- | -------------------------------------------------------------------------------------------- |
| **Token-level**     | Measures token classification, not entity quality; downstream geocoding needs whole entities |
| **Relaxed/partial** | Downstream geocoding needs exact character offsets; partial matches are not actionable       |
| **Text-only match** | Ignores span boundaries, which matter for multi-word entities and sentence context           |

## Consequences

### Positive

- Simple, unambiguous metric (FP/FN counts are deterministic)
- Matches industry standard (CoNLL), making results comparable
- Clear signal: only perfectly correct entities count
- Easy to compute and explain to stakeholders
- Per-type breakdown reveals which entity types need improvement
- Combined with language detection accuracy, gives full picture of Stages 1-2

### Negative

- Strict matching means entity-boundary edge cases (e.g., "New York" vs "New\nYork") count as wrong even when the entity type is correct
- Small annotation errors in expected corpus cause misleading scores
- Does not capture "close but wrong boundary" improvements

### Neutral

- Expected corpus must be carefully annotated (minimal boundary ambiguity)
- May want to adopt a secondary relaxed metric later if exact scores plateau
- Future ADR will cover geocoding and event location evaluation

## Test Corpus Requirements

The evaluation corpus must be:

- Stored in-repo at `tests/corpus/` as JSON files
- Annotated with exact character offsets and entity types
- Cover both English and French
- Include edge cases: empty text, no entities, multiple entities, ambiguous mentions
- Each sample includes expected language code

### Recommended Corpus Size

| Category                                       | English                     | French                      | Rationale        |
| ---------------------------------------------- | --------------------------- | --------------------------- | ---------------- |
| Simple sentences (1-2 locations)               | 15 docs (~50 entities)      | 15 docs (~50 entities)      | Baseline quality |
| Full news paragraphs (3-5 locations)           | 15 docs (~80 entities)      | 15 docs (~80 entities)      | Realistic load   |
| Edge cases (empty, no locations, misspellings) | 10 docs (~20 entities)      | 10 docs (~20 entities)      | Robustness       |
| **Total**                                      | **40 docs (~150 entities)** | **40 docs (~150 entities)** |                  |

**~150 entities per language** balances annotation effort against statistical reliability:

- 50 entities → harmonic mean (F1) is ±~7% (too noisy)
- 150 entities → F1 is ±~4% (acceptable for MVP)
- 500+ entities → F1 is ±~2% (robust)

Per-type breakdown (GPE vs LOC) needs at least ~30 entities per type to be meaningful.

### Corpus Schema

```json
{
  "samples": [
    {
      "text": "The meeting in Paris was attended by officials from London.",
      "language": "en",
      "entities": [
        { "text": "Paris", "label": "GPE", "start": 16, "end": 21 },
        { "text": "London", "label": "GPE", "start": 59, "end": 65 }
      ]
    }
  ]
}
```

## Implementation

The evaluation tooling will live in `src/evaluation/` and be run as a standalone CLI command (separate from pytest):

```bash
uv run python -m src.evaluation
```

## Abbreviations

| Abbreviation | Meaning                                                                       |
| ------------ | ----------------------------------------------------------------------------- |
| **TP**       | True Positive — correctly predicted entity                                    |
| **FP**       | False Positive — predicted entity that does not exist in expected annotations |
| **FN**       | False Negative — actual entity that was not predicted                         |
| **P**        | Precision — TP / (TP + FP)                                                    |
| **R**        | Recall — TP / (TP + FN)                                                       |
| **F1**       | Harmonic mean of Precision and Recall — 2 × P × R / (P + R)                   |
| **GPE**      | Geopolitical Entity (spaCy label for countries, cities, states)               |
| **LOC**      | Non-GPE Location (spaCy label for rivers, mountains, regions)                 |
| **NER**      | Named Entity Recognition                                                      |
| **CoNLL**    | Conference on Natural Language Learning (origin of standard NER eval)         |

## Related Documents

- [Architecture Overview](../architecture/location-extraction.md)
- [ADR-001: Location Extraction Approach](ADR-001-location-extraction-approach.md)
