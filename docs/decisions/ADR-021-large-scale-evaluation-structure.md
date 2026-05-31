# ADR-021: Large-Scale Evaluation Structure

## Status

Proposed

## Date

2026-05-30

## Context

ADR-019 originally selected UNER v2 (English) + WikiNER-fr-gold (French) as gold-standard evaluation corpus sources. UNER v2's legacy dataset script is incompatible with `datasets>=3.0.0`, so the English source was switched to WikiANN (`unimelb-nlp/wikiann`) — a Wikipedia-derived NER dataset with LOC entities, free license, and native parquet support. We now need a concrete plan for how to convert these datasets, where to place the resulting corpus files, how they integrate with the existing evaluation runner (`src/evaluation/`), and whether the evaluation infrastructure should live inside or outside the service directory.

### Requirements

| Priority | Requirement                                                    |
| -------- | -------------------------------------------------------------- |
| **P0**   | No large binary / JSON files in the git repo                   |
| **P1**   | Large corpus evaluation must "just work" with minimal ceremony |
| **P2**   | Existing hand-written corpora continue to work unchanged       |
| **P3**   | CI pipeline (pytest) is unaffected                             |

### Current State

- 6 hand-written corpus files live in `tests/corpus/` (138 samples total, committed to git)
- `discover_corpora()` globs `tests/corpus/*.json` — flat, no recursion
- Evaluation CLI (`uv run python -m src.evaluation`) runs all discovered corpora
- CI (`scripts/ci.sh`) runs pytest only — never runs the evaluation CLI
- Conversion requires `datasets` (Hugging Face), which is not currently a dependency

## Decision

### 1. Everything Lives Inside the Service

Avoid a separate evaluation repository or top-level directory. All corpus files, conversion scripts, and evaluation code stay within `backend/location-extraction-service/`.

### 2. Lazy-Generated Corpora (Not Stored in Git)

Large corpus files are **never committed** to the repository. Instead, they are generated on demand and cached locally. The evaluation runner auto-detects whether the files exist and generates them lazily on first use.

**Cache location**: `tests/corpus/{en_wikiann,fr_wikiner_gold}.json` — same directory as hand-written corpora (so they're auto-discovered by glob), but added to `.gitignore`.

| File                                | Source                | Lang | Samples | Git? |
| ----------------------------------- | --------------------- | ---- | ------- | ---- |
| `tests/corpus/en_wikiann.json`      | WikiANN (HuggingFace) | EN   | ~7K     | No   |
| `tests/corpus/fr_wikiner_gold.json` | WikiNER-fr-gold       | FR   | ~12K    | No   |

**Generation flow**:

```
uv run python -m src.evaluation
  → discover_corpora() checks for en_wikiann.json
  → missing → import scripts.convert_en_wikiann → download + convert + write
  → caches at tests/corpus/en_wikiann.json
  → subsequent runs read from cache (instant)
```

The conversion step prints a clear message and shows a `tqdm` progress bar.

### 3. Conversion Scripts as Importable Modules

Two new scripts under `scripts/`, designed to be both runnable as CLI and importable from the evaluation runner:

| Script                             | Source                | Language | Output file                            |
| ---------------------------------- | --------------------- | -------- | -------------------------------------- |
| `scripts/convert_en_wikiann.py`    | WikiANN (HuggingFace) | EN       | `tests/corpus/en_wikiann.json`         |
| `scripts/convert_wikiner_fr.py`    | WikiNER-fr-gold       | FR       | `tests/corpus/fr_wikiner_gold.json`    |

Each script exposes a `convert(output_path: str) -> None` function that:

1. Loads the Hugging Face dataset using the `datasets` library
2. Reconstructs the original text from tokens (joining with spaces)
3. Computes character offsets for each entity span
4. Filters to samples containing ≥1 location entity
5. Maps all location entity types to `LOC`
6. Writes in the existing corpus JSON format (`{"samples": [...]}`)

Running standalone (one-time generation, e.g., for geocoding annotation):

```bash
uv run convert-en-wikiann
uv run convert-wikiner-fr
```

### 4. Dependency Management

Add `datasets>=3.0.0` and `tqdm>=4.66.0` to `[dependency-groups] dev` in `pyproject.toml`. Both are only needed for corpus generation, not for the service itself or its evaluation runtime. Grouping under `dev` keeps setup simple — every dev install gets the corpus-generation capability.

The evaluation runner guards the import with a `try/except ImportError` — if `datasets` is not installed, the large corpora are silently skipped (the hand-written corpora still work fine).

### 4a. Entry Points

The conversion scripts are registered as `[project.scripts]` entry points so they can be invoked with `uv run`:

```toml
[project.scripts]
convert-en-wikiann = "scripts.convert_en_wikiann:main"
convert-wikiner-fr = "scripts.convert_wikiner_fr:main"
```

Usage: `uv run convert-en-wikiann` instead of `uv run python scripts/convert_en_wikiann.py`.

### 5. Evaluation Runner Changes

**`discover_corpora()`** is modified to:

1. Run the existing glob for all `*.json` files (picks up hand-written + any cached large files)
2. For each expected large corpus file that is missing, attempt to import the corresponding conversion module and call `convert(output_path)`
3. If `datasets` is unavailable (`ImportError`), skip silently
4. Return all discovered + newly generated files sorted

The per-corpus evaluation path (`evaluate_corpus(path)`) is unchanged — it already accepts any valid corpus path.

The aggregate path (`evaluate_all_corpora()`) picks up generated files automatically through `discover_corpora()`.

### 6. NER-Only Corpora

Large-scale corpora are **NER-only**. They contain `text`, `language`, and `entities` fields but no geocoding annotations (`expected_geocoded_locations` / `expected_event_location`).

The hand-written corpora remain the sole source for geocoding evaluation — their smaller size makes manual verification feasible, and their annotations are crafted to cover specific edge cases (ambiguous names, natural features, etc.).

The `scripts/annotate_geocoding.py` `CORPUS_FILES` list is **not updated** for the large corpora, so the annotation script will never attempt to Nominatim-annotate 15K+ entities.

### 7. Evaluation Workflow

| Use case                             | Command / behavior                                                       |
| ------------------------------------ | ------------------------------------------------------------------------ |
| **All corpora (comprehensive)**      | `uv run python -m src.evaluation` — auto-generates large if missing      |
| **Hand-written only (fast)**         | `uv run python -m src.evaluation tests/corpus/en_simple.json` (per file) |
| **Single large corpus**              | `uv run python -m src.evaluation tests/corpus/en_wikiann.json`           |
| **Regenerate from scratch**          | `rm tests/corpus/en_wikiann.json` then re-run evaluation                 |
| **Pre-generate (e.g., for CI prep)** | `uv run convert-en-wikiann`                                              |

The comprehensive run (~20K samples) takes minutes. This is acceptable because it's an explicit, intentional command — not part of CI or daily dev workflow.

### 8. CI Impact

**Zero.** CI runs `scripts/ci.sh`, which executes pytest (unit + integration tests), linting, and formatting checks. The evaluation CLI is never invoked by CI.

### 9. File Lifecycle

```
git clone → tests/corpus/ has 6 hand-written files only
         → uv sync --dev (datasets installed)
         → uv run python -m src.evaluation (triggers generation)
         → tests/corpus/en_wikiann.json appears (gitignored)
         → subsequent evaluations read from cache
```

### 10. Expected Output Sizes

| File                   | Samples | Size   |
| ---------------------- | ------- | ------ |
| `en_wikiann.json`      | ~7,000  | ~2 MB  |
| `fr_wikiner_gold.json` | ~3,800  | ~1.5 MB|

Smaller than initially anticipated — WikiNER-fr-gold's BIOES encoding yields ~3,800 LOC samples rather than 8–12K — but still comfortably above the 1,000-sample minimum and well within local cache limits.

## Consequences

### Positive

- **Zero repo bloat**: ~22 MB of corpus data never enters git history
- **Seamless UX**: `uv run python -m src.evaluation` works out of the box — no separate setup step to remember
- **No CI impact**: Pytest-only CI means large corpora add zero pipeline time
- **Auto-discovery**: Existing runner picks up generated files without config changes
- **Backward compatible**: All 6 hand-written corpora work exactly as before
- **Supplement, not replace**: Hand-written corpora remain the quick-feedback loop; large corpora provide statistical rigor
- **Deep module**: Conversion scripts hide token reconstruction, offset computation, and HuggingFace dataset handling behind a narrow `convert(output_path)` interface
- **Ergonomic CLI**: Entry points (`uv run convert-en-wikiann`) simplify explicit corpus generation

### Negative

- **First-run latency**: Initial `uv run python -m src.evaluation` downloads + converts datasets for several minutes (mitigated by `tqdm` progress bar and cache reuse on subsequent runs)
- **`datasets` dependency**: Adds ~200 MB to dev install (mitigated by graceful fallback — evaluation proceeds without it)
- **Not reproducible without generation**: A fresh clone requires network access + datasets library to evaluate large corpora (the hand-written 138 samples always work without any setup)

### Neutral

- Conversion scripts are importable modules — usable from CLI, runner, or notebook
- If spaCy models or the geocoding pipeline change significantly, re-running evaluation reuses the cached corpus (no re-download needed)
- The cache is a regular JSON file; users can delete it to force regeneration
- Large corpora are NER-only; geocoding evaluation continues to rely on hand-written corpora with manually verified annotations

## Related Documents

- [ADR-019: Evaluation Corpus Sources](ADR-019-evaluation-corpus-sources.md)
- [ADR-002: NER Evaluation Protocol](ADR-002-ner-evaluation-protocol.md)
- [ADR-008: Geocoding Evaluation Corpus](ADR-008-geocoding-evaluation-corpus.md)
- [Evaluation Guide](../evaluation.md)
