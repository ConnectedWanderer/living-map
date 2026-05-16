# Context: Fix Doc-Implementation Inconsistencies

## Goal

Fix all inconsistencies between documentation (AGENTS.md, README.md, `docs/architecture/location-extraction.md`, ADRs) and the actual implementation in `backend/location-extraction-service/`.

## Discovered Issues

| #   | Severity | File(s)                                                    | Problem                                                                                                                                                    | Status                            |
| --- | -------- | ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| 1   | CRITICAL | `Dockerfile:25`                                            | CMD uses `src:app` but `src/__init__.py` doesn't export `app` — container fails on startup                                                                 | FIXED                             |
| 2a  | MAJOR    | `docs/architecture/location-extraction.md` Stage 3         | `GeoResult` code example missing `failures: list[EntityMention]` field                                                                                     | FIXED                             |
| 2b  | MAJOR    | `docs/architecture/location-extraction.md` Stage 4         | Stale `infer_event_location` function — should be `DisambiguatePipeline` with correct formula (`position * type_multiplier(2.5) * preposition_boost(1.3)`) | FIXED                             |
| 2c  | MAJOR    | `docs/architecture/location-extraction.md` Tech Stack      | Missing `pycountry` dependency                                                                                                                             | FIXED                             |
| 2d  | MAJOR    | `docs/architecture/location-extraction.md` Records table   | Missing `GeoResult` (with `failures`), `DisambiguateResult`, `NerResult`, `LocationResult` rows                                                            | FIXED                             |
| 3a  | MODERATE | `src/orchestrator.py:18`, `pyproject.toml:66`              | Stale "text2geo" references (replaced by geonamescache per ADR-007)                                                                                        | FIXED                             |
| 3b  | MODERATE | `docs/architecture/location-extraction.md` File Structure  | References non-existent Node.js files, omits `test_evaluation_integration.py`, `__init__.py`                                                               | FIXED                             |
| 3c  | MODERATE | `docs/architecture/location-extraction.md` Service diagram | References Node.js backend that doesn't exist in this repo                                                                                                 | FIXED                             |
| 4a  | MODERATE | `docs/decisions/ADR-006`                                   | Status says "All candidates implemented" but Candidate 5 text says "deferred"                                                                              | FIXED                             |
| 4b  | MODERATE | `docs/architecture/location-extraction.md` Phase 1b        | Says "wired into NER pipeline for regression detection" but it's a standalone CLI                                                                          | FIXED                             |
| 5a  | MINOR    | `AGENTS.md` structure block                                | Missing `__init__.py` in `src/` tree                                                                                                                       | FIXED                             |
| 5b  | MINOR    | `AGENTS.md`                                                | Undocumented `scripts/annotate_geocoding.py`                                                                                                               | FIXED                             |
| 5c  | MINOR    | `README.md` Related Docs                                   | Omits ADR-006, ADR-007 which AGENTS.md references                                                                                                          | FIXED                             |
| 3d  | MODERATE | `tests/integration/test_pipeline_integration.py:12`        | Stale "text2geo" reference in mock class docstring                                                                                                         | FIXED (found during verification) |

## Decisions

- **Node.js refs**: Remove entirely (doesn't exist in this repo)
- **Dockerfile CMD**: Fix to `src.app:app` (matches local dev)
- **Evaluation wiring**: Update wording to "Standalone CLI evaluation", keep checkbox

## Changes Made

| File                                                       | Change                                                                                                                                            |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Dockerfile:25`                                            | `src:app` → `src.app:app`                                                                                                                         |
| `src/orchestrator.py:18`                                   | "text2geo" → "geonamescache" in docstring                                                                                                         |
| `pyproject.toml:66`                                        | "text2geo data" → "geonamescache data" in marker                                                                                                  |
| `tests/integration/test_pipeline_integration.py:12`        | "text2geo" → "geonamescache" in docstring                                                                                                         |
| `docs/architecture/location-extraction.md` Stage 3         | Added `failures` field to `GeoResult` code example                                                                                                |
| `docs/architecture/location-extraction.md` Stage 4         | Replaced stale `infer_event_location` with `DisambiguatePipeline` — correct scoring formula, `pycountry` import, `DisambiguateResult` return type |
| `docs/architecture/location-extraction.md` Tech Stack      | Added `pycountry` row                                                                                                                             |
| `docs/architecture/location-extraction.md` Records table   | Added `GeoResult`, `DisambiguateResult`, `NerResult`, `LocationResult` rows                                                                       |
| `docs/architecture/location-extraction.md` File Structure  | Removed Node.js refs, added `__init__.py`, added `test_evaluation_integration.py`, clarified `test_nlp_manager.py`                                |
| `docs/architecture/location-extraction.md` Service diagram | Removed Node.js backend subgraph, simplified to show LocationPipeline composition                                                                 |
| `docs/architecture/location-extraction.md` Phase 1b        | "wired into NER pipeline" → "Standalone CLI evaluation wired into CI pipeline"                                                                    |
| `docs/decisions/ADR-006`                                   | Candidate 5: removed "deferred" language, documented actual implementation                                                                        |
| `AGENTS.md`                                                | Added `__init__.py` to src tree, added `annotate_geocoding.py` command                                                                            |
| `README.md`                                                | Added ADR-006, ADR-007 to Related Documentation                                                                                                   |

## Verification

- `bash scripts/format.sh --check` (repo root) — **Prettier + Ruff pass**
- `uv run python -m pytest -m "not model_dependent"` — **80 tests passed, 27 deselected** (model_dependent)
- Dockerfile CMD verified: `src.app:app` (correct)
- No remaining stale "text2geo" references outside of ADR content/filenames (historical, correct)
