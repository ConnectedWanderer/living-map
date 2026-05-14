# ADR-003: NER Pipeline Seam and Evaluation Module Restructuring

## Status

Accepted

## Date

2026-05-14

## Context

The location extraction service defines a 4-stage pipeline (language detection → NER → geocoding → event location inference). Currently only stages 1-2 (language detection + NER entity extraction) are implemented, spread across three thin modules in `src/pipeline/`:

| Module           | Lines | Role                        |
| ---------------- | ----- | --------------------------- |
| `detector.py`    | 30    | langdetect wrapper          |
| `nlp_manager.py` | 36    | spaCy model loading/caching |
| `extractor.py`   | 32    | GPE/LOC entity filtering    |

These modules are individually testable but have no orchestration layer — the wiring between them lives in `src/evaluation/__init__.py` inside `evaluate_corpus()`, which is the only function that calls detection and extraction together. This creates several problems:

1. **Pipeline orchestration in the wrong module.** Adding stages 3-4 (geocoding, disambiguation) would require duplicating the wiring or further bloating `evaluate_corpus`, which was designed per ADR-002 to evaluate only stages 1-2.

2. **Evaluation mixes three concerns.** `evaluate_corpus()` combines file I/O (`load_corpus`), pipeline orchestration (calling detector + extractor), and metric computation (`evaluate()`) in a single function. There is no seam to substitute the pipeline with a mock during unit tests.

3. **Shallow module.** `src/evaluation/corpus.py` exports a single 7-line function (`load_corpus`) that only `evaluation/__init__.py` imports.

4. **Library/CLI boundary is fuzzy.** `src/evaluation/__init__.py` contains file discovery (`discover_corpora`, `evaluate_all_corpora`) alongside pure metric computation (`evaluate()`), while `__main__.py` duplicates orchestration logic.

### Scope

This ADR covers restructuring of the NER pipeline (stages 1-2) and the evaluation module. Geocoding (stage 3) and event location inference (stage 4) are explicitly out of scope — they will be built on the other side of the seam defined here.

## Decision

### 1. Create a `NerPipeline` class in `src/pipeline/`

A new `NerPipeline` class composes detection and extraction behind a single interface:

```
src/pipeline/
├── __init__.py       # NerPipeline class, NerResult dataclass (public API)
├── detector.py       # internal: detect_language()
├── nlp_manager.py    # internal: get_ner_model(), cache_clear()
└── extractor.py      # internal: extract_location_mentions()
```

```python
@dataclass
class NerResult:
    language: str
    entities: list[dict]  # {text, label, start, end}
    model_name: str | None

class NerPipeline:
    def run(self, text: str) -> NerResult: ...
```

The return type is a dataclass (not Pydantic). Pydantic models belong at the API boundary in `src/models/schemas.py`; the intermediate pipeline result is internal plumbing.

### 2. Restructure `src/evaluation/` into three layers

```
src/evaluation/
├── __init__.py       # pure computation: evaluate(), _compute_rates(), _sum_metrics()
├── runner.py         # I/O + orchestration: load_corpus(), evaluate_corpus(), evaluate_all_corpora(), discover_corpora()
└── __main__.py       # CLI entry point (imports from runner.py, not __init__.py)
```

**`__init__.py`** becomes purely computational — no file I/O, no imports from `src.pipeline`. Only `evaluate()` and its private helpers.

**`runner.py`** absorbs `load_corpus` (from the deleted `corpus.py`) plus orchestration functions. `evaluate_corpus` accepts an optional `NerPipeline` parameter:

```python
def evaluate_corpus(corpus_path: str, pipeline: NerPipeline | None = None) -> dict:
    pipeline = pipeline or NerPipeline()
    samples = load_corpus(corpus_path)
    ...
```

This creates a seam for testing without running spaCy.

**`__main__.py`** imports from `runner.py` instead of `__init__.py`.

**Delete `src/evaluation/corpus.py`** — its single function inlines into `runner.py`.

### 3. Keep evaluation scoped to stages 1-2

Per ADR-002, the evaluation module measures language detection + NER quality. Restructuring does not change this scope. The runner module depends on `NerPipeline` but has no knowledge of geocoding or disambiguation.

## Consequences

### Positive

- Pipeline orchestration lives in the pipeline module, not the evaluation module — a single place to wire stages.
- `evaluate_corpus` accepts an injectable pipeline: unit tests can mock `NerPipeline` and skip spaCy; CLI/production use the real pipeline.
- `evaluate()` becomes a pure function in a pure module, independently testable without file I/O or pipeline dependencies.
- Evaluation module structure matches responsibility boundaries (pure compute vs. orchestration vs. CLI).
- Future geocoding/disambiguation pipeline classes follow the same pattern (`GeoPipeline`, etc.) on the other side of the seam.

### Negative

- Existing imports from `src.evaluation.corpus` or `src.evaluation` that relied on the old function locations must be updated (cost is low — only internal code and tests are affected).
- `evaluation/__main__.py` gains a trivial dependency on `runner.py`; one additional import to understand.

### Neutral

- `corpus.py` is deleted — one less file, but developers accustomed to the original structure need to locate `load_corpus` in `runner.py`.
- `NerResult` is a dataclass rather than Pydantic model; this is intentional (API boundary vs. internal plumbing separation) but may be questioned by developers who prefer uniform typing.

## Related Documents

- [Architecture Overview](../architecture/location-extraction.md)
- [ADR-001: Location Extraction Approach](ADR-001-location-extraction-approach.md)
- [ADR-002: NER Quality Evaluation Protocol](ADR-002-ner-evaluation-protocol.md)
