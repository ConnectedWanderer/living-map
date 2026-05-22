import cron from 'node-cron';
import type { SourceRow } from './config.ts';

/** Register per-source cron jobs. Returns a stop function to cancel all. */
export function startScheduler(
  sources: SourceRow[],
  runFn: (source: SourceRow) => Promise<void>,
): () => void {
  const tasks = sources.map((source) =>
    cron.schedule(source.schedule, () => {
      runFn(source);
    }),
  );

  return () => {
    for (const task of tasks) task.stop();
  };
}
