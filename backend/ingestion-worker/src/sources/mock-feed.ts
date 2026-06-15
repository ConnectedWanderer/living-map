import { XMLParser } from 'fast-xml-parser';
import type { NormalizedArticle } from '../normalizer.ts';
import { normalizeArticle } from '../normalizer.ts';
import type { FetchDeps, SourceConfig } from './adapter.ts';

interface RssItem {
  title?: string;
  link?: string;
  guid?: string;
  pubDate?: string;
  description?: string;
}

interface RssChannel {
  item?: RssItem | RssItem[];
}

interface RssRoot {
  rss?: {
    channel?: RssChannel;
  };
}

const FETCH_TIMEOUT_MS = 15_000;

/** Fetch and parse an RSS feed from the configured URL. */
export async function fetchArticles(
  config: SourceConfig,
  deps?: FetchDeps,
): Promise<NormalizedArticle[]> {
  const fetchFn = deps?.fetch || global.fetch;
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), FETCH_TIMEOUT_MS);
  const response = await fetchFn(config.url, { signal: abort.signal });
  clearTimeout(timer);

  if (!response.ok) {
    throw new Error(`Failed to fetch RSS feed: ${response.status} ${response.statusText}`);
  }

  const xml = await response.text();
  const parser = new XMLParser({
    processEntities: false,
    stopNodes: ['*'],
  });
  const parsed = parser.parse(xml) as RssRoot;

  const channel = parsed?.rss?.channel;
  if (!channel) {
    return [];
  }

  const items = Array.isArray(channel.item) ? channel.item : channel.item ? [channel.item] : [];

  return items.map((item) =>
    normalizeArticle(
      {
        guid: item.guid,
        title: item.title || '',
        description: item.description,
        link: item.link || '',
        pubDate: item.pubDate || '1970-01-01T00:00:00.000Z',
      },
      config.source,
    ),
  );
}
