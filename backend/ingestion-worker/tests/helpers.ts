import { execSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import pg from 'pg';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export function createTestPool(connectionString: string): pg.Pool {
  return new pg.Pool({ connectionString });
}

export async function closePool(pool: pg.Pool): Promise<void> {
  await pool.end();
}

export async function runMigrations(connectionString: string): Promise<void> {
  execSync('npx node-pg-migrate up --migrations-dir ../migrations', {
    cwd: path.resolve(__dirname, '..'),
    env: { ...process.env, DATABASE_URL: connectionString },
    stdio: 'pipe',
  });
}

export async function cleanTables(pool: pg.Pool): Promise<void> {
  await pool.query('TRUNCATE events, sources CASCADE');
}
