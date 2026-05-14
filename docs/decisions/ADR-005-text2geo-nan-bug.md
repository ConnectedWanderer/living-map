# ADR-005: text2geo GeoNames NaN Bug

## Status

Accepted

## Date

2026-05-14

## Context

The `text2geo` library (pinned via `text2geo @ git+https://github.com/charonviz/text2geo.git`) provides offline geocoding backed by GeoNames data. During CI setup and Docker builds, the data is downloaded by constructing a `Geocoder(dataset='world')` which triggers CSV download + index building.

The `_build_index()` method in `geocoder.py:136` calls `row["name"].lower()` on every row of the GeoNames CSV. Some rows have empty `name` cells which pandas parses as `float('nan')`, causing:

```
AttributeError: 'float' object has no attribute 'lower'
```

This was discovered when running `scripts/ci.sh` in a fresh environment. The spaCy model downloads succeeded, but the text2geo data download crashed CI.

## Decision

1. **CI script** (`scripts/ci.sh`): The text2geo download step uses `|| echo "Warning: ..."` to tolerate failure. The step prints a warning but does not halt the pipeline.

2. **No code change**: All geocoding tests (`tests/unit/test_geocoding.py`) mock `_geocode` at the module level. The real `Geocoder` is never instantiated during tests. The production Docker build is a separate concern (see Consequences).

3. **Track upstream**: This ADR records the issue for a future PR to `charonviz/text2geo` — the fix is trivial: replace `row["name"].lower()` with `str(row["name"]).lower()` at line 136 of `geocoder.py`. Alternatively, the project can fork the dependency if the upstream is unresponsive.

## Consequences

### Positive

- CI does not block on a non-critical dependency download failure.
- All 49 unit tests pass without the GeoNames dataset.
- The workaround is a one-line change (`|| echo`) — easy to audit and remove.

### Negative

- If geocoding is exercised in production without cached data, the service will fail to start. The Docker build step remains affected until the upstream fix or a fork is adopted.
- Silent failure in CI could mask future breakage of the data download (e.g., URL changes in GeoNames).

### Neutral

- Once upstream is patched or a fork is adopted, revert CI to fail-on-error (`set -e` resumes naturally) and remove the warning message and this ADR's status becomes Deprecated.
- The `text2geo` package version (0.1.0) is pinned via git commit — the fix could be adopted by bumping to a newer commit or switching to a forked repo.
