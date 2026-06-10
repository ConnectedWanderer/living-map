# AI Agent Instructions

See [README.md](README.md) for human docs.
See [architecture doc](../../docs/architecture/frontend.md) for design.
For repo-wide conventions (formatting, pre-commit) see [root AGENTS.md](../../AGENTS.md).

## Development Workflow

TDD: red-green-refactor, one behavior at a time, vertical slices only.

To add a test: create `src/<module>/<name>.test.ts` using Vitest + `@vue/test-utils`.

| Command              | Description                  |
| -------------------- | ---------------------------- |
| `npm run dev`        | Start Vite dev server        |
| `npm test`           | Run all tests                |
| `npm run test:watch` | Run tests in watch mode      |
| `npm run typecheck`  | TypeScript check (noEmit)    |
| `npm run build`      | Typecheck + production build |

## Code Conventions

- **Vue 3** with `<script setup lang="ts">` and Composition API
- **Pinia stores** use Options API (`defineStore` with `state`/`actions`)
- **Components**: props typed via `defineProps<{...}>()`, emits via `defineEmits<{...}>()`
- **Scoped CSS** for component styles, `main.css` for global resets
- **`maplibre-gl`** is a system boundary — mock at module level in tests via `vi.mock`
- **Test files** co-located with source: `events.ts` → `events.test.ts`
- **No hardcoded URLs** — use the Vite proxy (`/tiles` → backend)

## Structure

```
src/
├── main.ts                 # Vue + Pinia bootstrap
├── App.vue                 # Root, renders MapView
├── assets/styles/main.css  # Global reset, full-screen layout
├── stores/events.ts        # Pinia store (selectedFeature)
├── services/api.ts         # TILE_URL constant
└── components/
    ├── MapView.vue         # MapLibre deep module — init, tiles, circle layer, popup
    └── EventPopup.vue      # Popup overlay on marker click
```

## Troubleshooting

| Symptom                      | Fix                                                                                         |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| `vitest` not found           | `npm install`                                                                               |
| Type errors                  | `npx vue-tsc -b` to check                                                                   |
| MapLibre init error in tests | Mock `maplibre-gl` at top of test file using `vi.mock`                                      |
| No tiles loading in dev      | Backend API must be running on port 3002. Check Vite proxy config in `vite.config.ts`       |
| Pinia "getActivePinia" error | Call `setActivePinia(createPinia())` in `beforeEach` of store/component tests               |
| Build fails (typecheck)      | Run `vue-tsc -b` to find errors. Test files excluded from typecheck via `tsconfig.app.json` |

## Related Documentation

- [Architecture Doc](../../docs/architecture/frontend.md)
- [Architecture Overview](../../docs/architecture/overview.md)
