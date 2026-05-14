# ADR-004: Consolidate Pipeline Sub-Package into Single Module

## Status

Accepted

## Date

2026-05-14

## Context

The `src/pipeline/` sub-package contained four files totaling ~140 lines:

- `__init__.py` (42 lines) — `NerPipeline` class, `NerResult` dataclass
- `detector.py` (30 lines) — `detect_language()` wrapping langdetect
- `nlp_manager.py` (36 lines) — `get_ner_model()` with `@lru_cache`, `MODEL_MAP`, `cache_clear()`
- `extractor.py` (32 lines) — `extract_location_mentions()` filtering spaCy entities

Each file was 30–42 lines of actual logic, wrapping a single external dependency. Understanding the full NER pipeline required opening 4 files and tracing imports. The modules were explicitly marked "internal" in ADR-003, yet each lived at a file-level import path equally accessible as the public `NerPipeline` class.

Additionally, `src/geocoding/` was an empty directory with no `__init__.py` — a leftover from a prior version — and `src/models/` had a stale `__pycache__/`.

## Decision

1. Consolidate `src/pipeline/` (4 files) into `src/pipeline.py` (single module). Internal functions remain module-level (no `_` prefix) to preserve direct test imports, but are no longer in a separate sub-package.

2. Delete the stale `src/geocoding/` directory.

3. Remove the stale `__pycache__/` from `src/models/`.

## Consequences

### Positive

- ~140 lines of pipeline logic now lives in one file instead of four — no need to trace cross-module imports.
- Future pipeline stages (geocoding, disambiguation) can live as sibling modules (`geocoding.py`, `disambiguator.py`) rather than new sub-packages, keeping the same pattern.
- All existing imports continue to work: `from src.pipeline import NerPipeline` is unchanged; deep imports like `from src.pipeline.detector import detect_language` become `from src.pipeline import detect_language`.

### Negative

- Internal functions (`detect_language`, `get_ner_model`, `extract_location_mentions`) are no longer in separate namespaced files — less granularity for future independent reuse.
- ADR-003's explicit file layout is partially superseded.

### Neutral

- No behavioral changes to `NerPipeline.run()` or any public API surface.
- All 68 existing tests (48 unit, 20 integration) pass without modification to test logic — only import paths changed.
