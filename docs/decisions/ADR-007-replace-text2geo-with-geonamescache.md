# ADR-007: Replace text2geo with geonamescache

## Status

Accepted

## Context

The `text2geo` library (pinned via `git+https://github.com/charonviz/text2geo.git`) provides offline geocoding backed by GeoNames data. It was chosen during initial development for its simple API and offline operation.

Several issues have arisen:

1. **Maintenance risk**: The GitHub repository has only 3 commits total (initial commit + 2 README images). There are no releases on PyPI, no issue tracker activity, and only one contributor. The project cannot be relied upon for long-term maintenance.

2. **Known NaN bug** (ADR-005): `_build_index()` crashes on empty `name` cells in the GeoNames CSV (`AttributeError: 'float' object has no attribute 'lower'`). The fix requires forking or waiting for upstream — neither has happened.

3. **Data download fragility**: The Docker build and CI download GeoNames data at build time via `Geocoder(dataset='world')`. This step is error-prone and must tolerate failure with a warning.

4. **No PyPI release**: The dependency is pinned to a git commit, which is fragile — the repo could be deleted or force-pushed.

A replacement was sought that provides the same capabilities (offline, GeoNames-backed, country code lookup, city-to-coordinates) with active maintenance and a stable PyPI release.

## Options Considered

| Approach | Maintenance | Fuzzy Match | Offline | Complexity |
|----------|-------------|-------------|---------|------------|
| **geonamescache + rapidfuzz** | ✅ Active (Mar 2026) | ✅ Optional | ✅ Bundled | Low |
| DIY: cities500.txt + rapidfuzz | ✅ Weekly GeoNames updates | ✅ Optional | ✅ Download | Medium |
| Keep text2geo (vendor it) | ⚠️ Unknown | ✅ Built-in | ✅ Download | Lowest |
| Mordecai3 | ✅ Active | Partial | ❌ Needs ES | Very high |

Since exact name matching is sufficient (NER extracts canonical place names, fuzzy matching for typos is unnecessary), `geonamescache` alone — without `rapidfuzz` — covers the use case.

## Decision

Replace `text2geo` with `geonamescache>=3.0.1` as the offline geocoding backend.

Key reasons:
- **Actively maintained**: v3.0.1 released March 2026, 8 contributors, regular releases since 2012.
- **Bundled data**: City data ships with the pip package — no download step at build time, no NaN bug.
- **Exact matching sufficient**: The name index (primary name + all alternatenames, case-insensitive) resolves to highest-population city on collision — the same heuristic text2geo uses.
- **Stable PyPI package**: No git-pinned dependencies.
- **Lighter footprint**: No rapidfuzz dependency needed; smaller memory than text2geo's pandas-based index.

The `GeoPipeline` interface remains unchanged — this is a pure implementation swap behind the injectable `geocode_fn` seam.

## Consequences

### Positive

- Eliminates the CI/Docker data download fragility — no more `|| echo "Warning: text2geo data download failed"`.
- ADR-005 (NaN bug) becomes deprecated — the root cause is removed.
- Stable dependency management via PyPI version pinning.
- All 8 geocoding unit tests pass unchanged (they mock `_geocode` at the module level).

### Negative

- Slightly smaller city set by default (32K at default `min_city_population=15000` vs text2geo's 140K). Configurable via `min_city_population=500` to get 223K cities.
- No fuzzy matching for misspelled place names — if NER extracts a typo, it won't match. Acceptable for news text where proper nouns are typically spelled correctly.

### Neutral

- `uv.lock` regenerated.
- Docker image no longer downloads GeoNames data at build time — slightly faster builds.
