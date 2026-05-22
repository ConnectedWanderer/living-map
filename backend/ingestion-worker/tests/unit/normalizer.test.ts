import assert from 'node:assert';
import crypto from 'node:crypto';
import { describe, it } from 'node:test';
import { normalizeArticle } from '../../src/normalizer.ts';

describe('normalizeArticle', () => {
  it('uses guid as source_id when present', () => {
    const raw = {
      guid: 'abc-123',
      title: 'Flood in Paris',
      description: 'Major flooding reported',
      link: 'http://example.com/paris-flood',
      pubDate: '2026-01-15',
    };

    const result = normalizeArticle(raw, 'mock-feed');

    assert.strictEqual(result.source_id, 'abc-123');
    assert.strictEqual(result.title, 'Flood in Paris');
    assert.strictEqual(result.description, 'Major flooding reported');
    assert.strictEqual(result.url, 'http://example.com/paris-flood');
    assert.strictEqual(result.published_at, '2026-01-15T00:00:00.000Z');
    assert.strictEqual(result.source, 'mock-feed');
  });

  it('computes SHA-256 hash as source_id when guid is missing', () => {
    const raw = {
      title: 'Earthquake in Tokyo',
      description: 'Magnitude 6.5',
      link: 'http://example.com/tokyo-quake',
      pubDate: '2026-02-10',
    };

    const result = normalizeArticle(raw, 'mock-feed');

    const expectedHash = crypto
      .createHash('sha256')
      .update('Earthquake in Tokyo' + '2026-02-10')
      .digest('hex');

    assert.strictEqual(result.source_id, expectedHash);
    assert.strictEqual(result.title, 'Earthquake in Tokyo');
    assert.strictEqual(result.description, 'Magnitude 6.5');
    assert.strictEqual(result.url, 'http://example.com/tokyo-quake');
    assert.strictEqual(result.published_at, '2026-02-10T00:00:00.000Z');
    assert.strictEqual(result.source, 'mock-feed');
  });
});
