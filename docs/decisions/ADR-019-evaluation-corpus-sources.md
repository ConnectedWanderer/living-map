# ADR-019: Evaluation Corpus Sources — UNER v2 (EN) + WikiNER-fr-gold (FR)

## Status

Accepted

## Date

2026-05-27

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

## Decision

Use **UNER v2 (English) + WikiNER-fr-gold (French)**, both gold-standard and
freely licensed.

### Source 1: UNER v2 (English)

- **Dataset**: `universalner/universal_ner` on Hugging Face
- **Splits**: `en_ewt` (train 12,543 / dev 2,001 / test 2,077) + `en_pud`
  (test 1,000) — carried forward unchanged from v1
- **Entity types**: LOC, PER, ORG (no GPE/LOC distinction — acceptable per
  earlier decision)
- **Domain**: Universal Dependencies treebanks (web text for EWT, news/Wikipedia
  for PUD)
- **License**: CC BY 4.0 (v2) / CC-BY-SA-4.0 (v1 legacy)
- **Quality**: Gold-standard, human-annotated

### Source 2: WikiNER-fr-gold (French)

- **Dataset**: `danrun/WikiNER-fr-gold` on Hugging Face
- **Size**: 26,818 sentences, ~700K tokens
- **Entity types**: LOC, PER, ORG, MISC
- **Domain**: Wikipedia
- **License**: Free (derived from WikiNER, manually revised to gold quality)
- **Quality**: Gold-standard — fully human-revised from the original silver-
  standard WikiNER

### Conversion approach

1. Download both datasets from Hugging Face
2. Convert token-level IOB2 → entity-level spans with character offsets
3. Filter for sentences containing ≥1 LOC entity
4. Map entity types: all location entities → `LOC` in project schema (no GPE
   distinction needed)
5. Output as `en_uner.json` and `fr_wikiner_gold.json` in existing corpus format
6. Add geocoding ground truth via `scripts/annotate_geocoding.py`
7. Validate offsets with `scripts/fix_corpus_offsets.py --check`

### Expected output size (after filtering for LOC only)

| Language | Source            | Raw sentences | Estimated LOC-filtered |
| -------- | ----------------- | ------------- | ---------------------- |
| English  | UNER v2 EWT + PUD | ~17.6K        | 5,000–7,000            |
| French   | WikiNER-fr-gold   | ~26.8K        | 8,000–12,000           |

## Consequences

### Positive

- Both sources are **gold-standard** human-annotated (P0 satisfied)
- Both languages are covered (P1 satisfied)
- Both are **freely licensed** (P2 satisfied)
- Both yield **well above** 1000 samples after filtering (P3 satisfied)
- UNER's LOC tag matches the project schema without mapping complexity
- WikiNER-fr-gold is the largest freely-available gold-standard French NER corpus
- Existing tooling (`annotate_geocoding.py`, `fix_corpus_offsets.py`) is reused
  as-is

### Negative

- Two different annotation schemes must be converted (IOB2 → entity spans)
  with separate scripts
- The two datasets come from different domains (UD treebanks vs. Wikipedia),
  which may surface different failure modes
- WikiNER-fr-gold includes MISC entities (e.g., nationalities, events) that are
  not location-related and must be filtered out
- UNER uses a single LOC tag, so if GPE/LOC distinction is ever needed later,
  the English corpus would lack that granularity

### Neutral

- WikiNER-fr-gold has no dev/test split — samples will be split during conversion
  or held out at evaluation time
- Entity frequency imbalance (more LOC in French) means per-language scores are
  not directly comparable by volume, but F1 normalizes for this

## Rejected Alternatives

| Alternative          | Reason for rejection                                       |
| -------------------- | ---------------------------------------------------------- |
| **WikiANN (both)**   | Silver-standard only — violates P0 (gold quality)          |
| **UNER-only (both)** | Neither v1 nor v2 covers French — hybrid is unavoidable    |
| **CoNLL-2003**       | French not available                                       |
| **NewsEye**          | French only, ~1.4K historical newspapers — no English pair |
| **OntoNotes 5**      | Requires LDC license (not free)                            |

## Related Documents

- [Evaluation Guide](../evaluation.md)
- [ADR-002: NER Evaluation Protocol](ADR-002-ner-evaluation-protocol.md)
- [ADR-008: Geocoding Evaluation Corpus](ADR-008-geocoding-evaluation-corpus.md)
