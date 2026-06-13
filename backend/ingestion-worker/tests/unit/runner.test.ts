import assert from 'node:assert';
import { describe, it } from 'node:test';
import type { NormalizedArticle } from '../../src/normalizer.ts';
import { runSource } from '../../src/runner.ts';

describe('runSource', () => {
  it('fetches articles and inserts them into the database', async () => {
    const articles: NormalizedArticle[] = [
      {
        source_id: 'a1',
        title: 'Article A',
        description: 'Desc A',
        url: 'http://a',
        published_at: '2026-01-01T00:00:00.000Z',
        source: 'mock-feed',
      },
    ];

    const config = {
      id: 1,
      name: 'test',
      type: 'mock-feed',
      config: { url: 'http://feed', source: 'mock-feed' },
      schedule: '*/5 * * * *',
    };

    let insertedArticles: NormalizedArticle[] | undefined;

    const deps = {
      fetch: async () => new Response(),
      pool: {} as import('pg').Pool,
      fetchArticles: async () => articles,
      insertEvents: async (_pool: import('pg').Pool, arts: NormalizedArticle[]) => {
        insertedArticles = arts;
        return { inserted: 1, skipped: 0 };
      },
      logger: {
        info: () => {},
        error: () => {},
        warn: () => {},
      } as unknown as import('pino').Logger,
    };

    await runSource(config, deps);

    assert.strictEqual(insertedArticles, articles);
  });
});
