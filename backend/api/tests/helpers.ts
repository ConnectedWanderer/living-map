import { execSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const migrationsDir = path.resolve(__dirname, '..', '..', 'migrations');

export async function runMigrations(connectionString: string): Promise<void> {
  execSync(
    `npx node-pg-migrate up --migration-file-language js --migrations-dir ${migrationsDir} --schema living_map`,
    {
      cwd: path.resolve(__dirname, '..'),
      env: { ...process.env, DATABASE_URL: connectionString },
      stdio: 'pipe',
    },
  );
}
