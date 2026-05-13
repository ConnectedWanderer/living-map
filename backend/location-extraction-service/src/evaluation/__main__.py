import sys

from src.evaluation.corpus import load_corpus


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.evaluation <corpus.json>", file=sys.stderr)
        sys.exit(1)

    corpus_path = sys.argv[1]
    samples = load_corpus(corpus_path)

    total_entities = sum(len(s["entities"]) for s in samples)
    languages = sorted({s["language"] for s in samples})
    label_counts = {}
    for s in samples:
        for e in s["entities"]:
            label_counts[e["label"]] = label_counts.get(e["label"], 0) + 1

    print(f"Corpus: {corpus_path}")
    print(f"Samples: {len(samples)}")
    print(f"Languages: {', '.join(languages)}")
    print(f"Total entities: {total_entities}")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")
    print()
    print("Pipeline evaluation requires spaCy models.")
    print("Run: uv run python -m spacy download en_core_web_sm fr_core_news_sm")


if __name__ == "__main__":
    main()
