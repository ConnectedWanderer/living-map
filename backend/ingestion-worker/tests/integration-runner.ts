/**
 * Integration test runner.
 *
 * Lifecycle:
 *   1. Validate that required Docker images exist.
 *   2. Start shared containers (mock-feed, LES) via Testcontainers.
 *   3. Run all `tests/integration/*.test.ts` files as a Node.js child
 *      process with MOCK_FEED_URL and LE_URL injected into the environment.
 *   4. Tear down containers in reverse order on completion (pass or fail).
 *
 * Each test file manages its own PostGIS database via @testcontainers/postgresql
 * (see setup.ts).  Only the two shared services live in the runner.
 */

import { spawn, execSync } from 'node:child_process';
import { readdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { GenericContainer, type StartedTestContainer, Wait } from 'testcontainers';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ingestionWorkerDir = resolve(__dirname, '..');
const integrationDir = resolve(__dirname, 'integration');

const MOCK_FEED_PORT = 3001;
const LE_PORT = 8000;

const MOCK_FEED_TAG = 'living-map/mock-feed:latest';
const LE_DEPS_TAG = 'living-map/le-deps:latest';
const LE_TAG = 'living-map/location-extraction:latest';

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

function startLocationExtractionService(): Promise<{
  url: string;
  container: StartedTestContainer;
}> {
  return new GenericContainer(LE_TAG)
    .withExposedPorts(LE_PORT)
    .withWaitStrategy(Wait.forHttp('/health', LE_PORT).withStartupTimeout(120_000))
    .start()
    .then((container) => ({
      url: `http://localhost:${container.getMappedPort(LE_PORT)}`,
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

async function getTestFiles(): Promise<string[]> {
  const files = await readdir(integrationDir);
  return files
    .filter((f) => f.endsWith('.test.ts'))
    .map((f) => resolve(integrationDir, f))
    .sort();
}

async function main(): Promise<void> {
  requireImage(MOCK_FEED_TAG, 'npm run docker:build:mock-feed');
  requireImage(LE_DEPS_TAG, 'npm run docker:build:le-deps');
  requireImage(LE_TAG, 'npm run docker:build:le');

  const containers: StartedTestContainer[] = [];

  try {
    console.log('[runner] Starting mock-feed ...');
    const mockFeed = await startMockFeed();
    containers.push(mockFeed.container);
    console.log(`[runner] mock-feed ready at ${mockFeed.url}`);

    console.log('[runner] Starting location-extraction-service (waiting for /health) ...');
    const le = await startLocationExtractionService();
    containers.push(le.container);
    console.log(`[runner] location-extraction-service ready at ${le.url}`);

    const testEnv = {
      MOCK_FEED_URL: mockFeed.url,
      LE_URL: le.url,
    };

    const testFiles = await getTestFiles();
    console.log(`[runner] Running ${testFiles.length} integration test file(s):`);
    for (const file of testFiles) {
      console.log(`  - ${file}`);
    }
    console.log(`[runner] MOCK_FEED_URL=${mockFeed.url}, LE_URL=${le.url}`);

    const exitCode = await spawnWithOutput(
      process.execPath,
      ['--test', '--experimental-strip-types', ...testFiles],
      { cwd: ingestionWorkerDir, env: testEnv },
    );

    console.log(`[runner] Tests completed with exit code ${exitCode}`);
    process.exit(exitCode);
  } finally {
    if (containers.length > 0) {
      console.log('[runner] Tearing down containers ...');
    }
    for (const container of containers.reverse()) {
      await container.stop();
    }
  }
}

main().catch((err) => {
  console.error('[runner] Integration tests failed:', err instanceof Error ? err.message : err);
  process.exit(1);
});
