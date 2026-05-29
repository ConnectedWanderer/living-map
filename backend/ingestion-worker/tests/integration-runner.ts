/**
 * Integration test runner.
 *
 * Lifecycle:
 *   1. Validate that required Docker images exist.
 *   2. Start shared containers (mock-feed, LES) via Testcontainers.
 *   3. Run all `tests/integration/*.test.ts` files as a Node.js child
 *      process with MOCK_FEED_URL and LOCATION_EXTRACTION_SERVICE_URL
 *      injected into the environment.
 *   4. Tear down containers on completion (pass or fail).
 */

import { spawn, execSync } from 'node:child_process';
import { readdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { GenericContainer, type StartedTestContainer, Wait } from 'testcontainers';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ingestionWorkerDir = resolve(__dirname, '..');
const integrationDir = resolve(__dirname, 'integration');

const MOCK_FEED_PORT = 3001;
const LOCATION_EXTRACTION_SERVICE_PORT = 8000;

const MOCK_FEED_TAG = 'living-map/mock-feed:latest';
const LOCATION_EXTRACTION_SERVICE_TAG = 'living-map/location-extraction-service:latest';

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
  return new GenericContainer(LOCATION_EXTRACTION_SERVICE_TAG)
    .withExposedPorts(LOCATION_EXTRACTION_SERVICE_PORT)
    .withWaitStrategy(
      Wait.forHttp('/health', LOCATION_EXTRACTION_SERVICE_PORT).withStartupTimeout(120_000),
    )
    .start()
    .then((container) => ({
      url: `http://localhost:${container.getMappedPort(LOCATION_EXTRACTION_SERVICE_PORT)}`,
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
  requireImage(LOCATION_EXTRACTION_SERVICE_TAG, 'npm run docker:build:location-extraction-service');

  const containers: StartedTestContainer[] = [];

  try {
    console.log('[runner] Starting mock-feed ...');
    const mockFeed = await startMockFeed();
    containers.push(mockFeed.container);
    console.log(`[runner] mock-feed ready at ${mockFeed.url}`);

    console.log('[runner] Starting location-extraction-service (waiting for /health) ...');
    const locationExtraction = await startLocationExtractionService();
    containers.push(locationExtraction.container);
    console.log(`[runner] location-extraction-service ready at ${locationExtraction.url}`);

    const testEnv = {
      MOCK_FEED_URL: mockFeed.url,
      LOCATION_EXTRACTION_SERVICE_URL: locationExtraction.url,
    };

    const testFiles = getTestFiles();
    console.log(`[runner] Running ${testFiles.length} integration test file(s):`);
    for (const file of testFiles) {
      console.log(`  - ${file}`);
    }
    console.log(
      `[runner] MOCK_FEED_URL=${mockFeed.url}, LOCATION_EXTRACTION_SERVICE_URL=${locationExtraction.url}`,
    );

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
