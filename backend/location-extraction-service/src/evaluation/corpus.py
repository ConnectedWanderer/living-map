import json


def load_corpus(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return data["samples"]
