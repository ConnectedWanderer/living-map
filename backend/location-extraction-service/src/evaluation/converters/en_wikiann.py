"""Convert WikiANN English dataset to evaluation corpus JSON.

Downloads ``unimelb-nlp/wikiann`` (English) from Hugging Face, reconstructs
text from tokens, extracts LOC entity spans from the ``spans`` field, and
writes in the existing corpus JSON format.

Usage:
    uv run python -m src.evaluation.converters.en_wikiann
    uv run python -m src.evaluation.converters.en_wikiann path/to/output.json

"""

import json
import os
import sys

from tqdm import tqdm


def _reconstruct_text(tokens: list[str]) -> str:
    """Reconstruct original text by joining tokens with spaces."""
    return " ".join(tokens)


def convert(output_path: str) -> None:
    """Download WikiANN English, extract LOC entities, and write JSON."""
    from datasets import load_dataset

    print("Generating en_wikiann corpus (first run, may take a few minutes)...")

    dataset = load_dataset("unimelb-nlp/wikiann", "en", split="train")

    samples: list[dict] = []
    for example in tqdm(dataset, desc="Converting WikiANN (EN)"):
        text = _reconstruct_text(example["tokens"])
        entities: list[dict] = []

        for span in example["spans"]:
            if not span.startswith("LOC:"):
                continue
            entity_text = span[4:].strip()
            start = text.find(entity_text)
            if start == -1:
                continue
            entities.append(
                {
                    "text": entity_text,
                    "label": "LOC",
                    "start": start,
                    "end": start + len(entity_text),
                }
            )

        if not entities:
            continue

        samples.append(
            {
                "text": text,
                "language": "en",
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
        output_path = "tests/corpus/en_wikiann.json"
    convert(output_path)


if __name__ == "__main__":
    main()
