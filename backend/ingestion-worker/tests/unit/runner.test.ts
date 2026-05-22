import assert from 'node:assert';
import { describe, it } from 'node:test';
import type { GeoJsonFeatureCollection } from '../../src/enrich.ts';
import { runSource } from '../../src/runner.ts';

describe('runSource', () => {
  it('fetches articles, inserts, enriches each, updates each, logs summary', async () => {
    const articles = [
      {
        source_id: 'a1',
        title: 'Article A',
        description: 'Desc A',
        url: 'http://a',
        published_at: '2026-01-01T00:00:00.000Z',
        source: 'mock-feed',
      },
      {
        source_id: 'a2',
        title: 'Article B',
        description: 'Desc B',
        url: 'http://b',
        published_at: '2026-01-02T00:00:00.000Z',
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

    const geoJson: GeoJsonFeatureCollection = { type: 'FeatureCollection', features: [] };

    let extractCalls = 0;
    let updateCalls = 0;
    const logInfoCalls: unknown[] = [];

    const deps = {
      fetch: async () => new Response(),
      pool: {} as unknown as import('pg').Pool,
      fetchArticles: async () => articles,
      insertEvents: async () => ({ inserted: 2, skipped: 0 }),
      updateLocation: async () => {
        updateCalls++;
      },
      extractLocation: async () => {
        extractCalls++;
        return geoJson;
      },
      locationExtractionUrl: 'http://le:8000',
      logger: {
        info: (obj: unknown) => {
          logInfoCalls.push(obj);
        },
        error: () => {},
        warn: () => {},
      } as unknown as import('pino').Logger,
    };

    await runSource(config, deps);

    assert.strictEqual(extractCalls, 2);
    assert.strictEqual(updateCalls, 2);
    assert.strictEqual(logInfoCalls.length, 1);
  });

  it('skips enrichment when all articles are duplicates', async () => {
    const articles = [
      {
        source_id: 'a1',
        title: 'Article A',
        description: undefined,
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

    let extractCalls = 0;
    let updateCalls = 0;
    const logInfoCalls: unknown[] = [];

    const deps = {
      fetch: async () => new Response(),
      pool: {} as unknown as import('pg').Pool,
      fetchArticles: async () => articles,
      insertEvents: async () => ({ inserted: 0, skipped: 1 }),
      updateLocation: async () => {
        updateCalls++;
      },
      extractLocation: async () => {
        extractCalls++;
        return null;
      },
      locationExtractionUrl: 'http://le:8000',
      logger: {
        info: (obj: unknown) => {
          logInfoCalls.push(obj);
        },
        error: () => {},
        warn: () => {},
      } as unknown as import('pino').Logger,
    };

    await runSource(config, deps);

    assert.strictEqual(extractCalls, 0);
    assert.strictEqual(updateCalls, 0);
    assert.strictEqual(logInfoCalls.length, 1);
  });
});
