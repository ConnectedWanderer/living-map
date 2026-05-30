import assert from 'node:assert';
import { before, describe, it } from 'node:test';
import { extractLocation } from '../../src/enrich.ts';
import { LOCATION_EXTRACTION_SERVICE_URL } from './helpers.ts';

describe('enrich integration', () => {
  before(async () => {
    const resp = await fetch(`${LOCATION_EXTRACTION_SERVICE_URL}/health`);
    if (!resp.ok) {
      throw new Error(`Location Extraction service not healthy at ${LOCATION_EXTRACTION_SERVICE_URL}`);
    }
  });

  it('extracts location from text via real LE service', async () => {
    const result = await extractLocation('There was a severe flood in Paris that damaged many buildings.', {
      url: LOCATION_EXTRACTION_SERVICE_URL,
    });

    assert.ok(result);
    assert.strictEqual(result.type, 'FeatureCollection');
    assert.ok(Array.isArray(result.features));
  });
});
