# Frontend

Vue 3 + Vite + MapLibre GL JS map viewer for the Living Map application. Renders event points as MVT tiles from the Serving API on a full-screen interactive map with globe projection.

## Features

- Full-screen interactive map with MapLibre GL JS v5
- Globe projection with auto-transition to Mercator at zoom ~5
- MVT tile source from the Serving API (`GET /tiles/{z}/{x}/{y}.pbf`)
- Circle layer with zoom-responsive radius scaling
- Popup with event details (title, source, date, location) on marker click
- Mobile-first responsive layout
- Type-safe with TypeScript + Vue 3 `<script setup>`

## Prerequisites

- **Node.js** v22+
- **npm**
- **Serving API** running on port 3002 (for tile data)

## Quick Start

### Local Development

```bash
# Clone and enter directory
cd frontend

# Install dependencies
npm install

# Start the dev server (Vite proxy /tiles → localhost:3002)
npm run dev
```

Open `http://localhost:5173` in a browser. The Vite dev server proxies `/tiles` requests to the Serving API.

> **Note**: The map requires the Serving API to be running with events in the database. See [`backend/api/README.md`](../../backend/api/README.md) for setup.

## Architecture

```
MapLibre GL JS → MVT tile source → GET /tiles/{z}/{x}/{y}.pbf → Serving API → PostGIS
```

```
src/
├── main.ts                 # Vue + Pinia bootstrap
├── App.vue                 # Root component, renders MapView full-screen
├── assets/styles/main.css  # Global reset, full-screen layout
├── stores/events.ts        # Pinia store (selectedFeature only — no event cache)
├── services/api.ts         # TILE_URL constant for the Vite proxy path
└── components/
    ├── MapView.vue         # MapLibre deep module — init, tiles, circle layer, popup
    └── EventPopup.vue      # Overlay with event details on marker click
```

- **MapView.vue** — The only deep module. Hides all MapLibre GL JS complexity behind a self-contained component with no props, emits, or slots. Pinia holds only `selectedFeature` (UI state); MapLibre manages the tile cache natively.
- **EventPopup.vue** — Receives `feature` prop with `EventProperties`, emits `close`.

## Configuration

| Variable      | Default                    | Description                  |
| ------------- | -------------------------- | ---------------------------- |
| `VITE_API_URL`| (not set, uses Vite proxy) | Future: direct API base URL  |

Dev server proxy is configured in `vite.config.ts` — `/tiles` → `http://localhost:3002`.

## Code Quality

```bash
npm run dev          # Start Vite dev server
npm test             # Run all tests (Vitest)
npm run test:watch   # Run tests in watch mode
npm run typecheck    # TypeScript check (no emit, vue-tsc)
npm run build        # Typecheck + production build
```

Tests use Vitest + `@vue/test-utils` with happy-dom environment. Test files are co-located with source: `events.ts` → `events.test.ts`.

## Related Documentation

- [Architecture Documentation](../../docs/architecture/frontend.md)
- [Architecture Overview](../../docs/architecture/overview.md)
- [Root README](../../README.md)
