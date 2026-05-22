import assert from 'node:assert';
import { after, before, describe, it, mock } from 'node:test';
import cron from 'node-cron';
import { startScheduler } from '../../src/scheduler.ts';

describe('startScheduler', () => {
  before(() => {
    mock.method(cron, 'schedule', (_expression: string, _func: string | (() => void)) => {
      return { stop: () => {} };
    });
  });

  after(() => {
    mock.restoreAll();
  });

  it('registers a cron job per source with correct expressions', () => {
    const sources = [
      { id: 1, name: 'feed-a', type: 'mock-feed', config: {}, schedule: '*/5 * * * *' },
      { id: 2, name: 'feed-b', type: 'mock-feed', config: {}, schedule: '0 * * * *' },
    ];

    const stop = startScheduler(sources, async () => {});

    const calls = (cron.schedule as unknown as { mock: { calls: Array<{ arguments: unknown[] }> } })
      .mock.calls;
    assert.strictEqual(calls.length, 2);
    assert.strictEqual(calls[0].arguments[0], '*/5 * * * *');
    assert.strictEqual(calls[1].arguments[0], '0 * * * *');

    stop();
  });
});
