import pg from "pg";
import path from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const TEST_DATABASE_URL =
  process.env.DATABASE_URL ||
  "postgres://livingmap:livingmap@localhost:5432/livingmap_test";

export function getTestDatabaseUrl(): string {
  return TEST_DATABASE_URL;
}

export async function createTestPool(): Promise<pg.Pool> {
  const pool = new pg.Pool({ connectionString: TEST_DATABASE_URL });
  return pool;
}

export async function closePool(pool: pg.Pool): Promise<void> {
  await pool.end();
}

export async function runMigrations(pool: pg.Pool): Promise<void> {
  const client = await pool.connect();
  try {
    await client.query("SELECT 1");
    execSync("npx node-pg-migrate up --migrations-dir ../migrations", {
      cwd: path.resolve(__dirname, ".."),
      env: { ...process.env, DATABASE_URL: TEST_DATABASE_URL },
      stdio: "pipe",
    });
  } finally {
    client.release();
  }
}

export async function cleanTables(pool: pg.Pool): Promise<void> {
  await pool.query("TRUNCATE events, sources CASCADE");
}
