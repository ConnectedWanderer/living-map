import assert from 'node:assert';
import { before, describe, it } from 'node:test';
import { fetchArticles } from '../../src/sources/mock-feed.ts';
import { MOCK_FEED_URL } from './helpers.ts';

describe('mock-feed adapter', () => {
  before(async () => {
    const resp = await fetch(`${MOCK_FEED_URL}/feed?count=1`);
    if (!resp.ok) {
      throw new Error(`Mock feed not healthy at ${MOCK_FEED_URL}`);
    }
  });

  it('fetches and normalizes articles from mock-feed', async () => {
    const articles = await fetchArticles({
      url: `${MOCK_FEED_URL}/feed?count=3`,
      source: 'mock-feed',
    });

    assert.strictEqual(articles.length, 3);
    for (const article of articles) {
      assert.ok(article.source_id);
      assert.ok(article.title);
      assert.ok(article.url);
      assert.ok(article.published_at);
      assert.strictEqual(article.source, 'mock-feed');
    }
  });
});
