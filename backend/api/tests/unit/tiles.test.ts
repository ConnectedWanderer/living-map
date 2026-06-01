import assert from 'node:assert/strict';
import { describe, it, mock } from 'node:test';
import type pg from 'pg';

describe('services/tiles', () => {
  it('getTile() returns null when query returns no rows', async () => {
    const mockPool = {
      query: mock.fn(() => Promise.resolve({ rows: [] })),
    } as unknown as pg.Pool;

    const { getTile } = await import('../../src/services/tiles.ts');
    const result = await getTile(mockPool, 5, 15, 10);
    assert.equal(result, null);
  });
});
