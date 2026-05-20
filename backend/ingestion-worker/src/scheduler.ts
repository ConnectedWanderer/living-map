import cron from "node-cron";
import type { SourceRow } from "./config.ts";

export function startScheduler(
  sources: SourceRow[],
  runFn: (source: SourceRow) => Promise<void>,
): () => void {
  const tasks = sources.map(source =>
    cron.schedule(source.schedule, () => {
      runFn(source);
    })
  );

  return () => {
    tasks.forEach(task => task.stop());
  };
}
