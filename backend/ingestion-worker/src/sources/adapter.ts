export interface SourceConfig {
  url: string;
  source: string;
}

export interface FetchDeps {
  fetch: typeof global.fetch;
}
