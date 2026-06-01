import assert from 'node:assert/strict';
import http from 'node:http';
import { describe, it } from 'node:test';

async function request(baseUrl: string, path: string): Promise<{ status: number; body: string }> {
  return new Promise((resolve, reject) => {
    http
      .get(`${baseUrl}${path}`, (res) => {
        let data = '';
        res.on('data', (chunk: string) => (data += chunk));
        res.on('end', () => resolve({ status: res.statusCode ?? 0, body: data }));
      })
      .on('error', reject);
  });
}

describe('index', () => {
  it('GET /health returns 200 with status ok', async () => {
    process.env.DATABASE_URL = 'postgres://user:pass@localhost:5432/testdb';
    process.env.PORT = '0';
    const { server } = await import('../../src/index.ts');
    try {
      const addr = server.address() as { port: number };
      const base = `http://localhost:${addr.port}`;
      const res = await request(base, '/health');
      assert.equal(res.status, 200);
      assert.deepEqual(JSON.parse(res.body), { status: 'ok' });
    } finally {
      server.close();
    }
  });
});
