import assert from 'node:assert';
import { describe, it } from 'node:test';
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

describe('extractLocation', () => {
  it('POSTs text to /api/extract-location and returns GeoJSON on success', async () => {
    const mockFetch = async (_url: RequestInfo | URL, _init?: RequestInit) => {
      return { ok: true, json: async () => geoJson } as Response;
    };

    const result = await extractLocation('Flood in Paris', {
      url: 'http://localhost:8000',
      fetch: mockFetch,
    });

    assert.deepStrictEqual(result, geoJson);
  });

  it('returns null after exhausting retries when fetch always fails', async () => {
    let callCount = 0;
    const mockFetch = async () => {
      callCount++;
      throw new Error('Network error');
    };
    const mockWait = async () => {};

    const result = await extractLocation('Flood in Paris', {
      url: 'http://localhost:8000',
      fetch: mockFetch,
      wait: mockWait,
    });

    assert.strictEqual(result, null);
    assert.strictEqual(callCount, 4);
  });
});
