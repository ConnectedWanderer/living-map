import assert from 'node:assert';
import { after, before, beforeEach, describe, it } from 'node:test';
import type pg from 'pg';
import { cleanTables } from '../helpers.ts';
import { LOCATION_EXTRACTION_SERVICE_URL, MOCK_FEED_URL } from './helpers.ts';
import { withPostgres } from './setup.ts';

describe('full cycle integration', () => {
  let pool: pg.Pool;
  let stop: () => Promise<void>;

  before(async () => {
    const resp = await fetch(`${MOCK_FEED_URL}/feed?count=1`);
    if (!resp.ok) {
      throw new Error(`Mock feed not healthy at ${MOCK_FEED_URL}`);
    }
    const leResp = await fetch(`${LOCATION_EXTRACTION_SERVICE_URL}/health`);
    if (!leResp.ok) {
      throw new Error(`Location Extraction service not healthy at ${LOCATION_EXTRACTION_SERVICE_URL}`);
    }

    const ctx = await withPostgres();
    pool = ctx.pool;
    stop = ctx.stop;
  });

  after(async () => {
    await stop();
  });

  beforeEach(async () => {
    await cleanTables(pool);
  });

  it('runs end-to-end: fetch, insert, enrich, update', async () => {
    const { fetchArticles } = await import('../../src/sources/mock-feed.ts');
    const { insertEvents, updateLocation } = await import('../../src/db.ts');
    const { extractLocation } = await import('../../src/enrich.ts');

    const articles = await fetchArticles({
      url: `${MOCK_FEED_URL}/feed?count=2`,
      source: 'full-cycle-test',
    });

    assert.strictEqual(articles.length, 2);

    const { inserted } = await insertEvents(pool, articles);
    assert.strictEqual(inserted, 2);

    const geoJson = await extractLocation('There was a severe flood in Paris that damaged many buildings.', { url: LOCATION_EXTRACTION_SERVICE_URL });
    assert.ok(geoJson);
    assert.ok(Array.isArray(geoJson.features));

    await updateLocation(pool, articles[0].source, articles[0].source_id, geoJson);

    const result = await pool.query('SELECT COUNT(*) AS count FROM events WHERE source = $1', [
      'full-cycle-test',
    ]);
    assert.strictEqual(Number(result.rows[0].count), 2);

    const geoResult = await pool.query(
      'SELECT ST_AsGeoJSON(location)::jsonb AS location FROM events WHERE source = $1 AND source_id = $2',
      ['full-cycle-test', articles[0].source_id],
    );
    const loc = geoResult.rows[0].location;
    assert.ok(loc);
    assert.strictEqual(loc.type, 'Point');
    assert.ok(Array.isArray(loc.coordinates));
    assert.strictEqual(loc.coordinates.length, 2);
  });
});
