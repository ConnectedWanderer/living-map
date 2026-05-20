import type { NormalizedArticle } from "./normalizer.ts";
import type { GeoJsonFeatureCollection } from "./enrich.ts";
import type { SourceRow } from "./config.ts";

interface FetchDeps {
  fetch: typeof global.fetch;
}

interface RunnerDeps {
  fetch: typeof global.fetch;
  pool: import("pg").Pool;
  fetchArticles: (config: Record<string, unknown>, deps?: FetchDeps) => Promise<NormalizedArticle[]>;
  insertEvents: (pool: import("pg").Pool, articles: NormalizedArticle[]) => Promise<{ inserted: number; skipped: number }>;
  updateLocation: (pool: import("pg").Pool, source: string, sourceId: string, geoJson: GeoJsonFeatureCollection) => Promise<void>;
  extractLocation: (text: string, config: { url: string }) => Promise<GeoJsonFeatureCollection | null>;
  locationExtractionUrl: string;
  logger: import("pino").Logger;
}

export async function runSource(
  sourceConfig: SourceRow,
  deps: RunnerDeps,
): Promise<void> {
  const articles = await deps.fetchArticles(sourceConfig.config, { fetch: deps.fetch });

  const { inserted } = await deps.insertEvents(deps.pool, articles);

  const newArticles = articles.slice(0, inserted);

  for (const article of newArticles) {
    const text = `${article.title} ${article.description || ""}`.trim();
    const geoJson = await deps.extractLocation(text, { url: deps.locationExtractionUrl });

    if (geoJson) {
      await deps.updateLocation(deps.pool, article.source, article.source_id, geoJson);
    }
  }

  deps.logger.info({ inserted, enriched: newArticles.length }, "Source cycle complete");
}
