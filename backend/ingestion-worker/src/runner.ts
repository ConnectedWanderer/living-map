import type { SourceRow } from './config.ts';
import type { NormalizedArticle } from './normalizer.ts';

interface FetchDeps {
  fetch: typeof global.fetch;
}

interface RunnerDeps {
  fetch: typeof global.fetch;
  pool: import('pg').Pool;
  fetchArticles: (
    config: Record<string, unknown>,
    deps?: FetchDeps,
  ) => Promise<NormalizedArticle[]>;
  insertEvents: (
    pool: import('pg').Pool,
    articles: NormalizedArticle[],
  ) => Promise<{ inserted: number; skipped: number }>;
  logger: import('pino').Logger;
}

/** Execute one full source cycle: fetch → insert → log. */
export async function runSource(sourceConfig: SourceRow, deps: RunnerDeps): Promise<void> {
  const articles = await deps.fetchArticles(sourceConfig.config, { fetch: deps.fetch });

  const { inserted } = await deps.insertEvents(deps.pool, articles);

  deps.logger.info({ inserted }, 'Source cycle complete');
}
