import pg from "pg";
import http from "http";
import { createLogger } from "./logger.ts";
import { loadSources } from "./config.ts";
import { startScheduler } from "./scheduler.ts";
import { runSource } from "./runner.ts";
import { extractLocation } from "./enrich.ts";
import { insertEvents, updateLocation } from "./db.ts";
import { fetchArticles as mockFeedFetch } from "./sources/mock-feed.ts";
import type { NormalizedArticle } from "./normalizer.ts";
import type { FetchDeps } from "./sources/adapter.ts";

interface Env {
  PORT?: string;
  DATABASE_URL?: string;
  LOCATION_EXTRACTION_URL?: string;
  LOG_LEVEL?: string;
}

function createFetchArticles(type: string): (config: Record<string, unknown>, deps?: FetchDeps) => Promise<NormalizedArticle[]> {
  switch (type) {
    case "mock-feed":
      return (config, deps) => mockFeedFetch(config as never, deps);
    default:
      throw new Error(`Unknown source type: ${type}`);
  }
}

export async function main(env: Env): Promise<http.Server> {
  const logger = createLogger(env.LOG_LEVEL);
  const pool = new pg.Pool({ connectionString: env.DATABASE_URL });

  const sources = await loadSources(pool);

  const stop = startScheduler(sources, (source) =>
    runSource(source, {
      fetch: global.fetch,
      pool,
      fetchArticles: createFetchArticles(source.type),
      insertEvents,
      updateLocation,
      extractLocation: (text) =>
        extractLocation(text, { url: env.LOCATION_EXTRACTION_URL || "" }),
      locationExtractionUrl: env.LOCATION_EXTRACTION_URL || "",
      logger,
    })
  );

  const server = http.createServer((req, res) => {
    if (req.url === "/health" && req.method === "GET") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok" }));
    } else {
      res.writeHead(404);
      res.end();
    }
  });

  const port = parseInt(env.PORT || "3000", 10);
  logger.info({ port }, "Server started");
  return server.listen(port);
}
