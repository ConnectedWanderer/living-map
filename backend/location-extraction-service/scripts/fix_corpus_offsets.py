"""Corpus offset validation and repair tools for NER evaluation corpora."""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CORPUS_DIR = os.path.join(BASE_DIR, "tests", "corpus")

DEFAULT_FILES = [
    "en_simple.json",
    "en_paragraphs.json",
    "en_edge_cases.json",
    "fr_simple.json",
    "fr_paragraphs.json",
    "fr_edge_cases.json",
]


def find_entity_positions(text: str, entity_text: str) -> list[tuple[int, int]]:
    """Find all (start, end) positions of entity_text in the given text.

    Args:
        text: The text to search within.
        entity_text: The substring to locate.

    Returns:
        List of (start, end) position tuples for each occurrence.

    """
    positions = []
    start = 0
    while True:
        pos = text.find(entity_text, start)
        if pos == -1:
            break
        positions.append((pos, pos + len(entity_text)))
        start = pos + 1
    return positions


def fix_corpus(path: str, dry_run: bool = False) -> dict:
    """Fix entity offset mismatches in a corpus JSON file.

    Args:
        path: Path to corpus JSON file.
        dry_run: If True, report fixes without writing.

    Returns:
        Dict with sample/entity/fixed/error counts and warnings.

    """
    with open(path) as f:
        data = json.load(f)

    stats = {"samples": 0, "entities": 0, "fixed": 0, "errors": 0, "warnings": []}

    for sample in data["samples"]:
        stats["samples"] += 1
        text = sample["text"]

        text_counts: dict[str, int] = {}

        for ent in sample["entities"]:
            stats["entities"] += 1
            entity_text = ent["text"]

            if entity_text not in text:
                stats["errors"] += 1
                stats["warnings"].append(f'  "{entity_text}" not found in text')
                continue

            positions = find_entity_positions(text, entity_text)

            text_counts[entity_text] = text_counts.get(entity_text, 0) + 1
            occurrence_index = text_counts[entity_text] - 1

            if occurrence_index >= len(positions):
                stats["errors"] += 1
                stats["warnings"].append(
                    f'  "{entity_text}" occurrence #{occurrence_index + 1} '
                    f"out of range ({len(positions)} found)"
                )
                continue

            correct_start, correct_end = positions[occurrence_index]

            if ent["start"] != correct_start or ent["end"] != correct_end:
                if not dry_run:
                    ent["start"] = correct_start
                    ent["end"] = correct_end
                stats["fixed"] += 1

            resolved = text[correct_start:correct_end]
            if resolved != entity_text:
                stats["errors"] += 1
                stats["warnings"].append(f'  verification failed for "{entity_text}"')

    if not dry_run:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    return stats


def check_corpus(path: str) -> dict:
    """Check entity offset correctness in a corpus file.

    Args:
        path: Path to corpus JSON file.

    Returns:
        Dict with entity/correct/wrong counts and per-sample details.

    """
    with open(path) as f:
        data = json.load(f)

    stats = {"entities": 0, "correct": 0, "wrong": 0, "details": []}
    for i, sample in enumerate(data["samples"]):
        text = sample["text"]
        for ent in sample["entities"]:
            stats["entities"] += 1
            actual = text[ent["start"] : ent["end"]]
            if actual == ent["text"]:
                stats["correct"] += 1
            else:
                stats["wrong"] += 1
                stats["details"].append(
                    f'  Sample {i}: "{ent["text"]}" at [{ent["start"]}:{ent["end"]}] '
                    f'-> got "{actual}"'
                )
    return stats


def main():
    """CLI entry point for fixing or checking corpus offsets."""
    import argparse

    parser = argparse.ArgumentParser(description="Fix entity offsets in evaluation corpus files.")
    parser.add_argument(
        "files", nargs="*", help="Corpus file(s) to process (default: all in tests/corpus/)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--check", action="store_true", help="Only check offsets, don't fix")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-file details")

    args = parser.parse_args()

    if args.files:
        paths = [os.path.join(BASE_DIR, f) if not os.path.isabs(f) else f for f in args.files]
    else:
        paths = [os.path.join(CORPUS_DIR, f) for f in DEFAULT_FILES]

    for path in paths:
        if not os.path.exists(path):
            print(f"File not found: {path}", file=sys.stderr)
            continue

        if args.check:
            stats = check_corpus(path)
            filename = os.path.basename(path)
            pct = stats["wrong"] / stats["entities"] * 100 if stats["entities"] else 0
            print(
                f"{filename}: {stats['correct']}/{stats['entities']} correct, "
                f"{stats['wrong']} wrong ({pct:.1f}%)"
            )
            if args.verbose and stats["details"]:
                for d in stats["details"]:
                    print(d)
        else:
            stats = fix_corpus(path, dry_run=args.dry_run)
            filename = os.path.basename(path)
            action = "Would fix" if args.dry_run else "Fixed"
            print(f"{filename}: {action} {stats['fixed']} entities ({stats['entities']} total)")
            if stats["warnings"]:
                for w in stats["warnings"]:
                    print(w)


if __name__ == "__main__":
    main()
