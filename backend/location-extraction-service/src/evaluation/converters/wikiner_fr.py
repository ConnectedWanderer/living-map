"""Convert WikiNER-fr-gold French dataset to evaluation corpus JSON.

Downloads ``danrun/WikiNER-fr-gold`` from Hugging Face, reconstructs
text from tokens, converts BIOES integer tags to entity-level spans,
filters to LOC entities, and writes in the existing corpus JSON format.

Usage:
    uv run python -m src.evaluation.converters.wikiner_fr
    uv run python -m src.evaluation.converters.wikiner_fr path/to/output.json

"""

import json
import os
import sys

from tqdm import tqdm

# BIOES tag encoding for WikiNER-fr-gold
# 0-O, 1-4=PER, 5-8=ORG, 9-12=LOC, 13-16=MISC
_LABELS: list[str] = [
    "O",
    "B-PER",
    "I-PER",
    "E-PER",
    "S-PER",
    "B-ORG",
    "I-ORG",
    "E-ORG",
    "S-ORG",
    "B-LOC",
    "I-LOC",
    "E-LOC",
    "S-LOC",
    "B-MISC",
    "I-MISC",
    "E-MISC",
    "S-MISC",
]


def _reconstruct_and_extract(tokens: list[str], tags: list[int]) -> tuple[str, list[dict]]:
    """Reconstruct text from tokens and extract LOC entity spans.

    Tracks character positions during reconstruction for accurate offsets.
    Handles BIOES encoding for LOC entities (tags 9-12).
    """
    token_positions: list[tuple[int, int]] = []
    pos = 0

    for i, token in enumerate(tokens):
        if i > 0:
            pos += 1
        token_positions.append((pos, pos + len(token)))
        pos += len(token)

    text = " ".join(tokens)

    entities: list[dict] = []
    ent_start: int | None = None

    for i, tag_id in enumerate(tags):
        tag = _LABELS[tag_id] if 0 <= tag_id < len(_LABELS) else "O"

        if tag == "B-LOC":
            if ent_start is not None:
                s = ent_start
                e = token_positions[i - 1][1]
                entities.append({"text": text[s:e], "label": "LOC", "start": s, "end": e})
            ent_start = token_positions[i][0]
        elif tag == "I-LOC":
            if ent_start is None:
                ent_start = token_positions[i][0]
        elif tag == "E-LOC":
            if ent_start is None:
                ent_start = token_positions[i][0]
            entities.append(
                {
                    "text": text[ent_start : token_positions[i][1]],
                    "label": "LOC",
                    "start": ent_start,
                    "end": token_positions[i][1],
                }
            )
            ent_start = None
        elif tag == "S-LOC":
            if ent_start is not None:
                s = ent_start
                e = token_positions[i - 1][1]
                entities.append({"text": text[s:e], "label": "LOC", "start": s, "end": e})
            entities.append(
                {
                    "text": text[token_positions[i][0] : token_positions[i][1]],
                    "label": "LOC",
                    "start": token_positions[i][0],
                    "end": token_positions[i][1],
                }
            )
            ent_start = None
        else:
            if ent_start is not None:
                s = ent_start
                e = token_positions[i - 1][1] if i > 0 else token_positions[i][0]
                entities.append({"text": text[s:e], "label": "LOC", "start": s, "end": e})
                ent_start = None

    if ent_start is not None:
        entities.append(
            {
                "text": text[ent_start:],
                "label": "LOC",
                "start": ent_start,
                "end": len(text),
            }
        )

    return text, entities


def convert(output_path: str) -> None:
    """Download WikiNER-fr-gold, convert, filter to LOC, and write JSON."""
    from datasets import load_dataset

    print("Generating fr_wikiner_gold corpus (first run, may take a few minutes)...")

    dataset = load_dataset("danrun/WikiNER-fr-gold", split="train")

    samples: list[dict] = []
    for example in tqdm(dataset, desc="Converting WikiNER-fr-gold"):
        text, entities = _reconstruct_and_extract(example["tokens"], example["ner_tags"])
        if not entities:
            continue

        samples.append(
            {
                "text": text,
                "language": "fr",
                "entities": entities,
            }
        )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"samples": samples}, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(
        f"Wrote {len(samples)} samples to {output_path} ({os.path.getsize(output_path) / 1024 / 1024:.1f} MB)"
    )


def main() -> None:
    """Run conversion from CLI with optional custom output path."""
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    else:
        output_path = "tests/corpus/fr_wikiner_gold.json"
    convert(output_path)


if __name__ == "__main__":
    main()
