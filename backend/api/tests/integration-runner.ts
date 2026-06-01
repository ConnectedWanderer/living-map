import { spawn } from 'node:child_process';
import { readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const apiDir = resolve(__dirname, '..');
const integrationDir = resolve(__dirname, 'integration');

function getTestFiles(): string[] {
  return readdirSync(integrationDir)
    .filter((f) => f.endsWith('.test.ts'))
    .map((f) => resolve(integrationDir, f))
    .sort();
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

async function main(): Promise<void> {
  const testFiles = getTestFiles();
  console.log(`[runner] Running ${testFiles.length} integration test file(s):`);
  for (const file of testFiles) {
    console.log(`  - ${file}`);
  }

  const exitCode = await spawnWithOutput(
    process.execPath,
    ['--test', '--experimental-strip-types', ...testFiles],
    { cwd: apiDir },
  );

  console.log(`[runner] Tests completed with exit code ${exitCode}`);
  process.exit(exitCode);
}

main().catch((err) => {
  console.error('[runner] Integration tests failed:', err instanceof Error ? err.message : err);
  process.exit(1);
});
