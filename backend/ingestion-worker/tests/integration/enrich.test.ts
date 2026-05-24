import assert from 'node:assert';
import { before, describe, it } from 'node:test';
import { extractLocation } from '../../src/enrich.ts';
import { LE_URL } from './helpers.ts';

describe('enrich integration', () => {
  before(async () => {
    const resp = await fetch(`${LE_URL}/health`);
    if (!resp.ok) {
      throw new Error(`Location Extraction service not healthy at ${LE_URL}`);
    }
  });

  it('extracts location from text via real LE service', async () => {
    const result = await extractLocation('Flood in Paris', {
      url: LE_URL,
    });

    assert.ok(result);
    assert.strictEqual(result.type, 'FeatureCollection');
    assert.ok(Array.isArray(result.features));
  });
});
