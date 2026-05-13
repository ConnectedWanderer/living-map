import sys

from src.evaluation import evaluate_corpus


def _fmt(v: float) -> str:
    return f"{v:.1%}" if isinstance(v, float) else str(v)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.evaluation <corpus.json>", file=sys.stderr)
        sys.exit(1)

    corpus_path = sys.argv[1]
    result = evaluate_corpus(corpus_path)

    print(f"Corpus: {result['corpus_path']}")
    print(f"Samples: {result['sample_count']}")
    print()
    print("Overall Metrics:")
    o = result["overall"]
    print(f"  Precision: {_fmt(o['precision'])}")
    print(f"  Recall:    {_fmt(o['recall'])}")
    print(f"  F1:        {_fmt(o['f1'])}")
    print(f"  TP: {o['tp']}  FP: {o['fp']}  FN: {o['fn']}")
    print()
    if result["per_type"]:
        print("Per-Type Metrics:")
        for label in sorted(result["per_type"]):
            pt = result["per_type"][label]
            print(f"  {label}:")
            print(f"    Precision: {_fmt(pt['precision'])}")
            print(f"    Recall:    {_fmt(pt['recall'])}")
            print(f"    F1:        {_fmt(pt['f1'])}")
            print(f"    TP: {pt['tp']}  FP: {pt['fp']}  FN: {pt['fn']}")
    print()
    print("Per-Sample Results:")
    for i, s in enumerate(result["samples"], 1):
        lang_match = "✓" if s["gold_language"] == s["detected_language"] else "✗"
        print(f"  {i}. [{s['gold_language']}→{s['detected_language']}{lang_match}] {s['text']}")


if __name__ == "__main__":
    main()
