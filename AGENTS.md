# AI Agent Instructions

## Setup

Required tools:

- **Node.js** (v22+) + npm
- **uv** — see https://docs.astral.sh/uv/
- **docker**, **docker-compose**, **docker-buildx** (to use current builder for docker images)

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
| `docs/`     | Both      | Deep architecture, ADRs, evaluation guides, glossary                                                              |

For project-specific abbreviations and domain terms, see [docs/glossary.md](docs/glossary.md).

## Integration Testing

- use Testcontainer instead of custom docker compose in Python and Node
- see `backend/ingestion-worker/tests/integration/setup.ts` for an example of Testcontainer usage
