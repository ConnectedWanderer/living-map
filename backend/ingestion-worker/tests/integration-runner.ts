import { spawn } from 'node:child_process';
import { readdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ingestionWorkerDir = resolve(__dirname, '..');
const backendDir = resolve(ingestionWorkerDir, '..');
const composeFile = resolve(backendDir, 'docker-compose.test.yml');
const integrationDir = resolve(__dirname, 'integration');

const testEnv = {
  DATABASE_URL: 'postgres://livingmap:livingmap@localhost:5432/livingmap_test',
  MOCK_FEED_URL: 'http://localhost:3001',
  LE_URL: 'http://localhost:8000',
};

function spawnWithOutput(
  cmd: string,
  args: string[],
  opts: { cwd?: string; env?: Record<string, string> } = {},
): Promise<number> {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, {
      stdio: 'inherit',
      cwd: opts.cwd,
      env: opts.env ? { ...process.env, ...opts.env } : process.env,
    });
    child.on('exit', (code) => resolve(code ?? 1));
    child.on('error', () => resolve(1));
  });
}

async function getTestFiles(): Promise<string[]> {
  const files = await readdir(integrationDir);
  return files
    .filter((f) => f.endsWith('.test.ts'))
    .map((f) => resolve(integrationDir, f))
    .sort();
}

async function main(): Promise<void> {
  const up = await spawnWithOutput('docker', ['compose', '-f', composeFile, 'up', '-d', '--wait']);
  if (up !== 0) {
    process.exit(1);
  }

  let exitCode = 0;
  try {
    const migrate = await spawnWithOutput(
      'npx',
      ['node-pg-migrate', 'up', '--migrations-dir', '../migrations'],
      { cwd: ingestionWorkerDir, env: testEnv },
    );
    if (migrate !== 0) {
      process.exit(1);
    }
    const testFiles = await getTestFiles();
    exitCode = await spawnWithOutput(
      process.execPath,
      ['--test', '--experimental-strip-types', ...testFiles],
      { cwd: ingestionWorkerDir, env: testEnv },
    );
  } finally {
    await spawnWithOutput('docker', ['compose', '-f', composeFile, 'down', '-v']);
  }

  if (exitCode !== 0) {
  }
  process.exit(exitCode);
}

main().catch((_err) => {
  process.exit(1);
});
