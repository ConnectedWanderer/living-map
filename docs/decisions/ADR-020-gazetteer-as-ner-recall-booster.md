# ADR-020: Gazetteer as NER Recall Booster (Not Replacement)

## Status

Accepted

## Date

2026-05-27

## Context

The spaCy NER stage (stages 1-2 of the pipeline) achieves an F1 score of ~50% using `en_core_web_sm` / `fr_core_news_sm`. This motivated an exploration of whether a deterministic text-matching approach against the Geonames database could replace the ML-based NER entirely, improving accuracy, reducing latency, and removing the spaCy dependency.

Three gazetteer-only approaches were evaluated:

### 1. Substring matching

Scan input text character-by-character, checking each substring against a trie of all geonames (names + alternatenames).

- **Word-boundary unaware** — "Al" inside "also" matches, "At" inside "Atlantic" matches
- Very noisy, many false positives from common-word geonames ("A", "In", "At", "By", "Go", "No", "Us", etc.)

### 2. N-gram matching (token-aware)

Tokenize text into words, generate n-grams (1-gram through ~5-grams), look up each n-gram in the geonames index, resolve overlaps via longest-match or highest population.

- **Word-boundary aware** — no partial-word matches
- Captures multi-word place names ("New York", "Buenos Aires")
- No context or disambiguation; "Paris Hilton" still matches "Paris"

### 3. Hybrid gazetteer (heuristic-filtered n-gram matching)

Same n-gram matching with filtering: stop-word removal, minimum name length, capitalization checks, entity-type inference from geonames feature codes (PPL → "LOC", ADM1 → "GPE", etc.).

- Closest approximation of NER without ML
- Entity type available from geonames feature codes, though mapping isn't 1:1 with GPE/LOC
- Requires non-trivial heuristic tuning to match NER precision

### Key Dependency

The disambiguator (stage 4) depends on `entity.type` for a **2.5× GPE multiplier**. A gazetteer-only approach would lose this signal unless feature-code mapping is added. NER also provides **character offsets** used in evaluation (CoNLL-style exact match), though not needed in production.

## Options Considered

| Option                       | Accuracy                       | Complexity                | Entity Types                     | Context Aware |
| ---------------------------- | ------------------------------ | ------------------------- | -------------------------------- | ------------- |
| **Keep spaCy NER (current)** | F1 ~50%                        | Low (existing)            | GPE/LOC from model               | Yes           |
| **Substring gazetteer**      | Very low precision             | Trivial                   | None                             | No            |
| **N-gram gazetteer**         | Higher recall, lower precision | Low                       | None                             | No            |
| **Hybrid gazetteer**         | Potentially comparable F1      | Medium (heuristic tuning) | From feature code (approximate)  | Minimal       |
| **Upgrade spaCy models**     | Unknown (likely higher)        | Lowest risk               | GPE/LOC from model               | Yes           |
| **spaCy + gazetteer boost**  | Potentially best               | Medium                    | GPE/LOC from NER + feature codes | Yes           |

## Decision

**Do not fully replace spaCy NER with a pure text-matching approach.** Three decisive reasons:

1. **Precision problem is harder than recall** — filtering out false positives from common-word geonames requires heuristics that effectively rebuild a GPE/LOC classifier, but worse.
2. **Entity type (GPE/LOC) is lost** — the disambiguator relies on it. Without it, event location accuracy degrades.
3. **Context awareness is lost** — a gazetteer cannot distinguish "I read about Paris" from "I visited Paris".

### Recommended path (in order)

1. **Upgrade spaCy models first** — try `en_core_web_md` (~40MB) and evaluate F1 improvement. Lowest-risk change.
2. **If accuracy still insufficient, add a gazetteer as a recall booster** — run both NER and n-gram gazetteer matching, deduplicate by character offset, and let the disambiguator score the combined set.
3. **Revisit after evaluation** — measure whether the hybrid approach improves F1, precision, and recall independently before committing to any removal of spaCy.

## Consequences

### Positive

- Retains context awareness and entity typing from spaCy NER
- Gazetteer booster can catch places NER misses, improving recall
- No regression to the disambiguator's GPE multiplier
- Backward compatible — gazetteer is additive, not replacive
- Low-risk first step (model upgrade) can be done independently

### Negative

- spaCy dependency and its ~40MB container footprint remain
- Two extraction paths to maintain if gazetteer boost is implemented
- Deduplication logic needed when both NER and gazetteer match the same mention
- Heuristic tuning of gazetteer filters may be ongoing work

### Neutral

- PDF report (this analysis) lives alongside the ADR as background
- Future evaluation may change the balance between NER and gazetteer components

## References

- [Gazetteer vs NER Analysis](../docs/gazetteer-vs-ner-analysis.md) — full analysis document
- [Architecture Documentation](../docs/architecture/location-extraction.md)
- [Evaluation Guide](../docs/evaluation.md)
- [ADR-001: Location Extraction Approach](ADR-001-location-extraction-approach.md)
- [ADR-007: Replace text2geo with geonamescache](ADR-007-replace-text2geo-with-geonamescache.md)
