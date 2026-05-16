# AI Agent Instructions

## Setup

Required tools:

- **Node.js** (v18+) + npm
- **uv** — see https://docs.astral.sh/uv/

## Code quality

Pre-commit hook runs `scripts/format.sh --check` before every commit.
The config lives in `.pre-commit-config.yaml`.

If the hook is not installed, run:

```bash
uv tool install pre-commit
pre-commit install
```

You can also run the check manually:

```bash
bash scripts/format.sh --check
```

## Documentation Conventions

Each component follows a consistent documentation structure:

| File        | Audience  | Content                                                                                                           |
| ----------- | --------- | ----------------------------------------------------------------------------------------------------------------- |
| `README.md` | Humans    | What, why, quick start, API usage, config, deployment                                                             |
| `AGENTS.md` | AI agents | Commands, code conventions, patterns, troubleshooting. Thin — references README + `docs/` rather than duplicating |
| `docs/`     | Both      | Deep architecture, ADRs, evaluation guides                                                                        |
