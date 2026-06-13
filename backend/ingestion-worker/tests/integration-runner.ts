import { execSync, spawn } from 'node:child_process';
import { readdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { GenericContainer, type StartedTestContainer } from 'testcontainers';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ingestionWorkerDir = resolve(__dirname, '..');
const integrationDir = resolve(__dirname, 'integration');

const MOCK_FEED_PORT = 3001;

const MOCK_FEED_TAG = 'living-map/mock-feed:latest';

function imageExists(tag: string): boolean {
  try {
    execSync(`docker image inspect ${tag}`, { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function requireImage(tag: string, buildHint: string): void {
  if (!imageExists(tag)) {
    console.error(`[runner] Missing required image: ${tag}`);
    console.error(`[runner] Build it with: ${buildHint}`);
    process.exit(1);
  }
}

function startMockFeed(): Promise<{ url: string; container: StartedTestContainer }> {
  return new GenericContainer(MOCK_FEED_TAG)
    .withExposedPorts(MOCK_FEED_PORT)
    .start()
    .then((container) => ({
      url: `http://localhost:${container.getMappedPort(MOCK_FEED_PORT)}`,
      container,
    }));
}

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
    child.on('error', (err) => {
      console.error('[runner] Failed to spawn test process:', err.message);
      resolve(1);
    });
  });
}

function getTestFiles(): string[] {
  return readdirSync(integrationDir)
    .filter((f) => f.endsWith('.test.ts'))
    .map((f) => resolve(integrationDir, f))
    .sort();
}

async function main(): Promise<void> {
  requireImage(MOCK_FEED_TAG, 'npm run docker:build:mock-feed');

  const containers: StartedTestContainer[] = [];

  try {
    console.log('[runner] Starting mock-feed ...');
    const mockFeed = await startMockFeed();
    containers.push(mockFeed.container);
    console.log(`[runner] mock-feed ready at ${mockFeed.url}`);

    const testEnv = {
      MOCK_FEED_URL: mockFeed.url,
    };

    const testFiles = getTestFiles();
    console.log(`[runner] Running ${testFiles.length} integration test file(s):`);
    for (const file of testFiles) {
      console.log(`  - ${file}`);
    }
    console.log(`[runner] MOCK_FEED_URL=${mockFeed.url}`);

    const exitCode = await spawnWithOutput(
      process.execPath,
      ['--test', '--experimental-strip-types', ...testFiles],
      { cwd: ingestionWorkerDir, env: testEnv },
    );

    console.log(`[runner] Tests completed with exit code ${exitCode}`);
    process.exit(exitCode);
  } finally {
    console.log('[runner] Cleaning up ...');
    for (const container of containers.reverse()) {
      await container.stop();
    }
  }
}

main().catch((err) => {
  console.error('[runner] Integration tests failed:', err instanceof Error ? err.message : err);
  process.exit(1);
});
