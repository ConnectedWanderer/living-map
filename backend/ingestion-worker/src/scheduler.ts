import cron from 'node-cron';
import type { SourceRow } from './config.ts';

/** Register per-source cron jobs. Returns a stop function to cancel all. */
export function startScheduler(
  sources: SourceRow[],
  runFn: (source: SourceRow) => Promise<void>,
  scheduleFn: typeof cron.schedule = cron.schedule,
): () => void {
  const tasks = sources.map((source) =>
    scheduleFn(source.schedule, () => {
      runFn(source);
    }),
  );

  return () => {
    for (const task of tasks) task.stop();
  };
}
