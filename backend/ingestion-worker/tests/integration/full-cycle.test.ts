import assert from 'node:assert';
import { after, before, beforeEach, describe, it } from 'node:test';
import type pg from 'pg';
import { cleanTables, closePool, createTestPool } from '../helpers.ts';
import { ensureServices, LE_URL, MOCK_FEED_URL } from './helpers.ts';

describe('full cycle integration', () => {
  let pool: pg.Pool;

  before(async () => {
    await ensureServices();
    pool = await createTestPool();
  });

  after(async () => {
    await closePool(pool);
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

    for (const article of articles) {
      const text = `${article.title} ${article.description || ''}`.trim();
      const geoJson = await extractLocation(text, { url: LE_URL });

      if (geoJson) {
        await updateLocation(pool, article.source, article.source_id, geoJson);
      }
    }

    const result = await pool.query('SELECT COUNT(*) AS count FROM events WHERE source = $1', [
      'full-cycle-test',
    ]);
    assert.strictEqual(Number(result.rows[0].count), 2);

    const geoResult = await pool.query(
      'SELECT location FROM events WHERE source = $1 AND source_id = $2',
      ['full-cycle-test', articles[0].source_id],
    );
    const loc = geoResult.rows[0].location;
    assert.ok(loc);
    assert.strictEqual(loc.type, 'Point');
    assert.ok(Array.isArray(loc.coordinates));
    assert.strictEqual(loc.coordinates.length, 2);
  });
});
