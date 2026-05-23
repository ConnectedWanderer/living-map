import assert from 'node:assert';
import { describe, it } from 'node:test';
import { startScheduler } from '../../src/scheduler.ts';

describe('startScheduler', () => {
  it('registers a cron job per source with correct expressions', () => {
    const sources = [
      { id: 1, name: 'feed-a', type: 'mock-feed', config: {}, schedule: '*/5 * * * *' },
      { id: 2, name: 'feed-b', type: 'mock-feed', config: {}, schedule: '0 * * * *' },
    ];

    const captured: string[] = [];
    const scheduleFn = ((expression: string) => {
      captured.push(expression);
      return { stop: () => {} };
    }) as unknown as typeof import('node-cron').schedule;

    const stop = startScheduler(sources, async () => {}, scheduleFn);

    assert.strictEqual(captured.length, 2);
    assert.strictEqual(captured[0], '*/5 * * * *');
    assert.strictEqual(captured[1], '0 * * * *');

    stop();
  });
});
