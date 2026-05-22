import assert from 'node:assert';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { extractLocation } from '../../src/enrich.ts';

const geoJson = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [2.35, 48.86] },
      properties: {},
    },
  ],
};

let originalFetch: typeof global.fetch;

describe('extractLocation', () => {
  beforeEach(() => {
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('POSTs text to /api/extract-location and returns GeoJSON on success', async () => {
    global.fetch = async (_url: RequestInfo | URL, _init?: RequestInit) => {
      return { ok: true, json: async () => geoJson } as Response;
    };

    const result = await extractLocation('Flood in Paris', { url: 'http://localhost:8000' });

    assert.deepStrictEqual(result, geoJson);
  });

  it('returns null after exhausting retries when fetch always fails', async () => {
    let callCount = 0;
    global.fetch = async () => {
      callCount++;
      throw new Error('Network error');
    };

    const origSetTimeout = global.setTimeout;
    global.setTimeout = ((fn: (...args: unknown[]) => void) => {
      fn();
      return {} as ReturnType<typeof setTimeout>;
    }) as typeof global.setTimeout;

    const result = await extractLocation('Flood in Paris', { url: 'http://localhost:8000' });

    global.setTimeout = origSetTimeout;

    assert.strictEqual(result, null);
    assert.strictEqual(callCount, 4);
  });
});
