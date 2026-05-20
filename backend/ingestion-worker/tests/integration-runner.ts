import { spawn } from "node:child_process";
import { readdir } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ingestionWorkerDir = resolve(__dirname, "..");
const backendDir = resolve(ingestionWorkerDir, "..");
const composeFile = resolve(backendDir, "docker-compose.test.yml");
const integrationDir = resolve(__dirname, "integration");

const testEnv = {
  DATABASE_URL: "postgres://livingmap:livingmap@localhost:5432/livingmap_test",
  MOCK_FEED_URL: "http://localhost:3001",
  LE_URL: "http://localhost:8000",
};

function spawnWithOutput(
  cmd: string,
  args: string[],
  opts: { cwd?: string; env?: Record<string, string> } = {},
): Promise<number> {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, {
      stdio: "inherit",
      cwd: opts.cwd,
      env: opts.env ? { ...process.env, ...opts.env } : process.env,
    });
    child.on("exit", (code) => resolve(code ?? 1));
    child.on("error", () => resolve(1));
  });
}

async function getTestFiles(): Promise<string[]> {
  const files = await readdir(integrationDir);
  return files
    .filter((f) => f.endsWith(".test.ts"))
    .map((f) => resolve(integrationDir, f))
    .sort();
}

async function main(): Promise<void> {
  console.log("Starting test services...");
  const up = await spawnWithOutput("docker", [
    "compose", "-f", composeFile, "up", "-d", "--wait",
  ]);
  if (up !== 0) {
    console.error("Failed to start test services");
    process.exit(1);
  }

  let exitCode = 0;
  try {
    console.log("\nRunning migrations...");
    const migrate = await spawnWithOutput("npx", [
      "node-pg-migrate", "up", "--migrations-dir", "../migrations",
    ], { cwd: ingestionWorkerDir, env: testEnv });
    if (migrate !== 0) {
      console.error("Migration failed");
      process.exit(1);
    }

    console.log("\nRunning integration tests...");
    const testFiles = await getTestFiles();
    exitCode = await spawnWithOutput(process.execPath, [
      "--test", "--experimental-strip-types", ...testFiles,
    ], { cwd: ingestionWorkerDir, env: testEnv });
  } finally {
    console.log("\nCleaning up test services...");
    await spawnWithOutput("docker", [
      "compose", "-f", composeFile, "down", "-v",
    ]);
  }

  if (exitCode !== 0) {
    console.error(`\nIntegration tests failed (exit code: ${exitCode})`);
  }
  process.exit(exitCode);
}

main().catch((err) => {
  console.error("Orchestrator error:", err);
  process.exit(1);
});
