import assert from 'node:assert/strict';
import { after, describe, it } from 'node:test';
import pg from 'pg';

describe('db/client', () => {
  const originalEnv = process.env.DATABASE_URL;

  after(() => {
    process.env.DATABASE_URL = originalEnv;
  });

  it('getPool() returns a pg.Pool instance', async () => {
    process.env.DATABASE_URL = 'postgres://user:pass@localhost:5432/testdb';
    const { getPool } = await import('../../src/db/client.ts');
    const pool = getPool();
    assert.ok(pool instanceof pg.Pool);
  });

  it('getPool() returns the same singleton on repeated calls', async () => {
    process.env.DATABASE_URL = 'postgres://user:pass@localhost:5432/testdb';
    const { getPool } = await import('../../src/db/client.ts');
    const a = getPool();
    const b = getPool();
    assert.equal(a, b);
  });

  it('closePool() drains and clears the singleton', async () => {
    process.env.DATABASE_URL = 'postgres://user:pass@localhost:5432/testdb';
    const { getPool, closePool } = await import('../../src/db/client.ts');
    const pool = getPool();
    await closePool();
    const newPool = getPool();
    assert.notEqual(pool, newPool);
    assert.ok(newPool instanceof pg.Pool);
  });
});
