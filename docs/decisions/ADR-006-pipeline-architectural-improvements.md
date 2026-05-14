# ADR-006: Pipeline Architectural Improvements

## Status

Accepted — All candidates implemented.

- Candidate 1 (Composed Pipeline Orchestrator)
- Candidate 2 (Geocoder Dependency Injection)
- Candidate 3 (Typed Intermediate Records)
- Candidate 4 (Split evaluate_corpus)
- Candidate 5 (Stages 3-4 Evaluation)

## Date

2026-05-14

## Context

The location extraction service has a 4-stage pipeline (language detection → spaCy NER → text2geo geocoding → event location inference) with all stages implemented in `src/pipeline.py`, `src/geocoding.py`, and `src/disambiguator.py`. After reviewing the codebase, architecture docs, and existing ADRs (ADR-001 through ADR-005), several structural friction points were identified.

The existing ADRs establish:

- ADR-001: spaCy + text2geo approach with 4-stage pipeline
- ADR-002: NER evaluation protocol scoped to stages 1-2 only
- ADR-003: `NerPipeline` class as the stages 1-2 seam (file-layout section superseded by ADR-004)
- ADR-004: Consolidation of pipeline sub-package into single module
- ADR-005: text2geo NaN bug with CI tolerance

### Friction Summary

1. **No composed pipeline orchestrator** — The three pipeline classes (`NerPipeline`, `GeoPipeline`, `DisambiguatePipeline`) exist in isolation. 16 integration tests in `test_pipeline_integration.py` are empty stubs because there is no composed seam to test against. Data flows between stages as untyped dicts with no contract enforcement.

2. **Global state in geocoder** — `_geocoder` is a module-level global initialized lazily. All geocoding tests patch `_geocode` at module path — a fragile seam that breaks on rename or relocation. No injection point for test doubles exists.

3. **Untyped dict flow between stages** — `NerResult.entities`, `GeoPipeline` input/output, and `DisambiguatePipeline` input are all `list[dict]`. Key mismatches exist (e.g., `GeoPipeline` drops the `type` field that `DisambiguatePipeline` reads). ADR-003/004 chose dataclasses for result types but the intermediate records remain untyped.

4. **`evaluate_corpus` mixes orchestration with metrics** — `evaluate_corpus()` both runs the pipeline and computes metrics. ADR-002 scopes evaluation to stages 1-2, but the function's dual responsibility makes it harder to reuse the runner for stages 3-4.

5. **No evaluation for stages 3-4** — ADR-002 explicitly deferred geocoding and disambiguation evaluation to a future ADR. Stages 3-4 are now implemented but have no quality measurement framework.

## Decision

We will pursue the following improvements in sequence:

### 1. Composed Pipeline Orchestrator

Create a `LocationPipeline` class that composes `NerPipeline`, `GeoPipeline`, and `DisambiguatePipeline` behind a single `run(text: str) -> LocationResult` interface. Define a typed `LocationResult` dataclass and typed intermediate record dataclasses (`EntityMention`, `GeocodedLocation`). Fill the 16 stub integration tests with real tests against this seam.

This does not change the behavior or interface of the existing individual pipeline classes. ADR-003's `NerPipeline` seam and ADR-004's single-module layout are preserved.

### 2. Geocoder Dependency Injection

Inject the `Geocoder` dependency into `GeoPipeline.__init__()` instead of using a module-level global. Keep a default for production convenience. Tests pass a fake geocoder instead of monkey-patching `_geocode`.

### 3. Typed Intermediate Records

Define `EntityMention` and `GeocodedLocation` dataclasses for exchange between pipeline stages. Update the existing result dataclasses (`NerResult`, `GeoResult`, `DisambiguateResult`) to use these types instead of `list[dict]`. This resolves the `type`-field mismatch between stages 3 and 4.

### 4. Split `evaluate_corpus` Concerns

Extract a `run_pipeline_on_corpus()` function from `evaluate_corpus()` so pipeline orchestration and metric computation are independently reusable. `evaluate_corpus()` becomes a thin composition of the two.

### 5. Stages 3-4 Evaluation (Future)

Add `expected_geocoded_locations` and `expected_event_location` fields to corpus samples and extend the evaluation runner. This is deferred until improvements 1-4 are in place, as they provide the infrastructure needed.

## Consequences

### Positive

- Composed pipeline creates a single seam for the API server, integration tests, and the evaluation runner — eliminating 16 stub tests.
- Injection-based geocoder enables clean testing without module-level patching (complements ADR-005's CI tolerance by making the test seam explicit).
- Typed intermediate records enforce contracts between stages at test time, catching mismatches like the missing `type` field.
- Cleaner separation in evaluation module enables stages 3-4 evaluation without further restructuring.
- All existing ADRs (ADR-001 through ADR-005) remain valid; no prior decisions are contradicted.

### Negative

- Changes to `GeoPipeline.__init__()` signature require updating all callers (currently only tests and the future composed pipeline).
- Typed records require updating dict-key accesses across pipeline classes and tests — mechanical but pervasive.
- The stages 3-4 evaluation (candidate 5) is deferred, leaving the quality measurement gap open longer.

### Neutral

- The individual pipeline classes (`NerPipeline`, `GeoPipeline`, `DisambiguatePipeline`) remain independently usable.
- ADR-003's `NerPipeline` seam and ADR-004's module layout are unchanged.
- The `LocationPipeline` follows the same `.run()` pattern as the existing pipeline classes.
