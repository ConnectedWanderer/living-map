import type { NormalizedArticle } from '../normalizer.ts';
import type { FetchDeps, SourceConfig } from './adapter.ts';
import { fetchArticles as mockFeedFetch } from './mock-feed.ts';

type FetchArticlesFn = (
  config: Record<string, unknown>,
  deps?: FetchDeps,
) => Promise<NormalizedArticle[]>;

const registry = new Map<string, FetchArticlesFn>();

/** Register a fetch function for a given source type. */
export function registerAdapter(type: string, fn: FetchArticlesFn): void {
  registry.set(type, fn);
}

/** Get the registered fetch function for a source type. Throws if unknown. */
export function getAdapter(type: string): FetchArticlesFn {
  const fn = registry.get(type);
  if (!fn) {
    throw new Error(`Unknown source type: ${type}`);
  }
  return fn;
}

function wrapAdapter(fn: (config: SourceConfig, deps?: FetchDeps) => Promise<NormalizedArticle[]>): FetchArticlesFn {
  return (config, deps) => fn(config as SourceConfig, deps);
}

registerAdapter('mock-feed', wrapAdapter(mockFeedFetch));
registerAdapter('rss', wrapAdapter(mockFeedFetch));
