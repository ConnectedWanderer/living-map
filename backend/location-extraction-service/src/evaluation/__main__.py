import os
import sys

from src.evaluation import DEFAULT_CORPUS_DIR, evaluate_all_corpora, evaluate_corpus

_GREEN = "\033[92m"
_RED = "\033[91m"
_RESET = "\033[0m"


def _fmt(v: float) -> str:
    return f"{v:.1%}" if isinstance(v, float) else str(v)


def _show_entities(label: str, entities: list[dict], match_set: set | None = None) -> None:
    if not entities:
        print(f"       {label}: (none)")
    else:
        for e in entities:
            key = (e["text"], e["label"], e["start"], e["end"])
            color = (
                _GREEN
                if match_set is not None and key in match_set
                else _RED
                if match_set is not None
                else ""
            )
            print(
                f"       {label}: {color}{e['text']} ({e['label']}, [{e['start']}:{e['end']}]){_RESET if color else ''}"
            )


def _print_single_corpus(result: dict) -> None:
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
        lang_match = "\u2713" if s["expected_language"] == s["detected_language"] else "\u2717"
        exp_set = {(e["text"], e["label"], e["start"], e["end"]) for e in s["expected_entities"]}
        pred_set = {(e["text"], e["label"], e["start"], e["end"]) for e in s["predicted_entities"]}
        tp = len(exp_set & pred_set)
        fp = len(pred_set - exp_set)
        fn = len(exp_set - pred_set)
        print(
            f"  {i}. [{s['expected_language']}\u2192{s['detected_language']}{lang_match}] tp={tp} fp={fp} fn={fn}  {s['text']}"
        )
        _show_entities("Expected", s["expected_entities"], pred_set)
        _show_entities("Predicted", s["predicted_entities"], exp_set)


def _print_synthesis(result: dict) -> None:
    if not result["corpora"]:
        print(f"No corpus files found in {DEFAULT_CORPUS_DIR}/")

        return

    total_samples = sum(c["sample_count"] for c in result["corpora"])
    print(f"Corpora: {len(result['corpora'])}  Total samples: {total_samples}")
    print()
    print("Aggregate Metrics (entity-level):")
    agg = result["aggregate"]
    o = agg["overall"]
    print(f"  Precision: {_fmt(o['precision'])}")
    print(f"  Recall:    {_fmt(o['recall'])}")
    print(f"  F1:        {_fmt(o['f1'])}")
    print(f"  TP: {o['tp']}  FP: {o['fp']}  FN: {o['fn']}")
    print()
    if agg["per_type"]:
        print("Per-type:")
        for label in sorted(agg["per_type"]):
            pt = agg["per_type"][label]
            print(
                f"  {label}:  Precision: {_fmt(pt['precision'])}  Recall: {_fmt(pt['recall'])}  F1: {_fmt(pt['f1'])}  TP: {pt['tp']}  FP: {pt['fp']}  FN: {pt['fn']}"
            )
    print()
    print("Per-Corpus Summary:")
    for c in result["corpora"]:
        o = c["overall"]
        print(
            f"  {os.path.basename(c['corpus_path']):30s}  {c['sample_count']:3d} samples    P={_fmt(o['precision'])}  R={_fmt(o['recall'])}  F1={_fmt(o['f1'])}"
        )
    print()
    print("Per-sample details available via: uv run python -m src.evaluation tests/corpus/<name>.json")


def main():
    if len(sys.argv) < 2:
        result = evaluate_all_corpora()
        _print_synthesis(result)
    else:
        corpus_path = sys.argv[1]
        result = evaluate_corpus(corpus_path)
        _print_single_corpus(result)


if __name__ == "__main__":
    main()
