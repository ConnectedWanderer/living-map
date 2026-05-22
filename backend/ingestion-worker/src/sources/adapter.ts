/** Configuration for a single source adapter. */
export interface SourceConfig {
  url: string;
  source: string;
}

/** Dependencies injected into source adapters for fetching. */
export interface FetchDeps {
  fetch: typeof global.fetch;
}
