# ADR-019: Evaluation Corpus Sources — WikiANN (EN) + WikiNER-fr-gold (FR)

## Status

Superseded (English source changed — see below)

## Date

2026-05-27 (updated 2026-05-31)

## Context

The existing hand-written evaluation corpus (`tests/corpus/`) has only 138 total
samples across 6 files — too small for statistically reliable NER metrics
(±~7% F1 at 50 entities). We need a large (1000+ samples), high-quality,
freely-licensed evaluation corpus in **both English and French** to measure
location NER accuracy.

### Requirements (ranked)

| Priority | Requirement                             |
| -------- | --------------------------------------- |
| **P0**   | Gold-standard (human-annotated) quality |
| **P1**   | Covers English AND French               |
| **P2**   | Freely licensed (no paywall / LDC fees) |
| **P3**   | 1000+ samples per language              |

### Candidates considered

| Corpus              | Gold? | EN  | FR  | Free? | Size (EN)       | Size (FR)        |
| ------------------- | ----- | --- | --- | ----- | --------------- | ---------------- |
| **CoNLL-2003**      | Yes   | Yes | No  | Yes   | ~22K sentences  | —                |
| **OntoNotes 5**     | Yes   | Yes | No  | No    | ~115K sentences | —                |
| **UNER v2**         | Yes   | Yes | No  | Yes   | ~17.6K\*        | —                |
| **WikiANN**         | No†   | Yes | Yes | Yes   | ~20K            | ~20K             |
| **WikiNER-fr-gold** | Yes   | —   | Yes | Yes   | —               | ~26.8K sentences |
| **NewsEye**         | Yes   | No  | Yes | Yes   | —               | ~1.4K documents  |

\* UNER v2 carries forward all v1 English data unchanged (`en_ewt`, `en_pud`). The v2 expansion adds 11 datasets in 10 new languages (Greek, Indonesian, Korean, Romanian, Slovenian, etc.) but French is not among them.

† WikiANN is silver-standard (automatically transferred from Wikipedia infoboxes).

No single gold-standard corpus covers both EN and FR for free. A hybrid is
required.

## Original Decision (Accepted 2026-05-27)

Use **UNER v2 (English) + WikiNER-fr-gold (French)**, both gold-standard and
freely licensed. See original ADR text below.

## Revision (2026-05-31): English Source Changed

UNER v2 uses a legacy ``universal_ner.py`` dataset script that is **incompatible
with ``datasets>=3.0.0``** (which dropped support for script-based loading in
favour of parquet/arrow). The English source is therefore switched to:

### Source 1 (revised): WikiANN (English)

- **Dataset**: ``unimelb-nlp/wikiann`` (English) on Hugging Face
- **Size**: 20,000 training sentences; ~7,000 contain LOC entities
- **Entity types**: PER, ORG, LOC
- **Domain**: Wikipedia (automatically annotated from infoboxes/category links)
- **License**: CC BY-SA (Wikipedia-derived)
- **Quality**: Silver-standard (automatic annotation propagated from structured
  Wikipedia data)
- **Compromise**: WikiANN is silver-standard, not gold. This trade-off is
  accepted because:
  - WikiANN annotations are consistently high-quality for named entities (PER,
    ORG, LOC) — Wikipedia infobox data is curated by editors
  - The large sample size (~7K LOC samples) provides statistical rigour that
    outweighs per-sample noise for aggregate NER metrics
  - The existing hand-written corpora (138 samples, gold-standard) remain
    available for precise per-sample debugging
  - WikiANN and WikiNER-fr-gold share the same Wikipedia domain, making
    cross-language comparisons more consistent

### Source 2 (unchanged): WikiNER-fr-gold (French)

- **Dataset**: `danrun/WikiNER-fr-gold` on Hugging Face
- **Size**: 26,818 sentences, ~700K tokens
- **Entity types**: LOC, PER, ORG, MISC
- **Domain**: Wikipedia
- **License**: Free (derived from WikiNER, manually revised to gold quality)
- **Quality**: Gold-standard — fully human-revised from the original silver-
  standard WikiNER

### Conversion approach (updated)

1. Download both datasets from Hugging Face
2. Reconstruct original text from tokens; compute character offsets
3. Filter for samples containing ≥1 LOC entity
4. Map all location entities → `LOC` in project schema
5. Output as `en_wikiann.json` and `fr_wikiner_gold.json` in existing corpus
   format
6. *(Large corpora are NER-only — no geocoding annotation)*

### Expected output size (after filtering for LOC only)

| Language | Source          | Raw sentences | Estimated LOC-filtered |
| -------- | --------------- | ------------- | ---------------------- |
| English  | WikiANN         | ~20K          | ~7,000                 |
| French   | WikiNER-fr-gold | ~26.8K        | ~3,800                 |

## Consequences

### Positive

- Both languages are covered (P1 satisfied)
- Both are **freely licensed** (P2 satisfied)
- Both yield **well above** 1000 samples after filtering (P3 satisfied)
- WikiANN and WikiNER-fr-gold share the same **Wikipedia domain**, making
  cross-language comparisons more consistent than UNER (UD) + WikiNER (Wikipedia)
- WikiNER-fr-gold is the largest freely-available gold-standard French NER corpus
- Existing tooling (`annotate_geocoding.py`, `fix_corpus_offsets.py`) is reused

### Negative

- WikiANN is **silver-standard** (automatic, not human-annotated) — P0 relaxed
  for English in favour of dataset availability and parquet compatibility
- The two datasets come from different annotation pipelines (WikiANN auto-tags
  vs. WikiNER human-revised)
- WikiNER-fr-gold includes MISC entities (e.g., nationalities, events) that are
  not location-related and must be filtered out

### Neutral

- WikiANN uses LOC/PER/ORG — GPE/LOC distinction is unavailable for either
  language
- Both datasets are Wikipedia-based, reducing cross-language domain mismatch
- The hand-written gold-standard corpora (138 samples) remain for precise
  evaluation

## Rejected Alternatives

| Alternative                    | Reason for rejection                                       |
| ------------------------------ | ---------------------------------------------------------- |
| **UNER v2**                    | Legacy script incompatible with `datasets>=3.0.0`          |
| **UNER-only (both)**           | Neither v1 nor v2 covers French — hybrid is unavoidable    |
| **CoNLL-2003**                 | French not available; also legacy script format            |
| **NewsEye**                    | French only, ~1.4K historical newspapers — no English pair |
| **OntoNotes 5**                | Requires LDC license (not free)                            |

## Related Documents

- [Evaluation Guide](../evaluation.md)
- [ADR-002: NER Evaluation Protocol](ADR-002-ner-evaluation-protocol.md)
- [ADR-008: Geocoding Evaluation Corpus](ADR-008-geocoding-evaluation-corpus.md)
