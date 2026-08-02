import type { Lane } from './spec';
import { describe, expect, it } from 'vitest';
import { createScheduler, type ScheduledJob } from './scheduler';

interface Deferred {
  job: ScheduledJob;
  finish: () => void;
}

function controllableJob(id: string, lane: Lane, eligible: () => boolean = () => true, priority = 1): Deferred {
  let finish!: () => void;
  const done = new Promise<void>((resolve) => {
    finish = resolve;
  });
  return { finish, job: { eligible, id, lane, priority, run: async () => done } };
}

const flush = async (): Promise<void> => new Promise(resolve => setTimeout(resolve, 0));

describe('createScheduler', () => {
  it('should start an eligible job immediately when a lane slot is free', () => {
    const scheduler = createScheduler();
    const a = controllableJob('a', 'default');
    scheduler.submit(a.job);
    expect(scheduler.isRunning('a')).toBe(true);
  });

  it('should respect the per-lane cap and start queued jobs as slots free', async () => {
    const scheduler = createScheduler({ balances: 2 }, 4);
    const jobs = ['a', 'b', 'c'].map(id => controllableJob(id, 'balances'));
    jobs.forEach(j => scheduler.submit(j.job));

    expect(scheduler.runningCount('balances')).toBe(2);
    expect(scheduler.isQueued('c')).toBe(true);

    jobs[0].finish();
    await flush();

    expect(scheduler.isRunning('c')).toBe(true);
    expect(scheduler.runningCount('balances')).toBe(2);
  });

  describe('lane families', () => {
    it('should cap a lane that no exact entry names', () => {
      const scheduler = createScheduler({}, 4, { 'tx-sync:': 2 });
      const jobs = ['a', 'b', 'c'].map(id => controllableJob(id, 'tx-sync:eth'));
      jobs.forEach(j => scheduler.submit(j.job));

      expect(scheduler.runningCount('tx-sync:eth')).toBe(2);
      expect(scheduler.isQueued('c')).toBe(true);
    });

    // The point of families: one cap per chain, not one cap shared by every chain.
    it('should give each lane in the family its own slots', () => {
      const scheduler = createScheduler({}, 4, { 'tx-sync:': 2 });
      ['a', 'b'].forEach(id => scheduler.submit(controllableJob(id, 'tx-sync:eth').job));
      ['c', 'd'].forEach(id => scheduler.submit(controllableJob(id, 'tx-sync:gnosis').job));

      expect(scheduler.runningCount('tx-sync:eth')).toBe(2);
      expect(scheduler.runningCount('tx-sync:gnosis')).toBe(2);
      expect(scheduler.runningCount()).toBe(4);
    });

    it('should let an exact cap override the family it falls under', () => {
      const scheduler = createScheduler({ 'tx-sync:eth': 1 }, 4, { 'tx-sync:': 2 });
      ['a', 'b'].forEach(id => scheduler.submit(controllableJob(id, 'tx-sync:eth').job));

      expect(scheduler.runningCount('tx-sync:eth')).toBe(1);
      expect(scheduler.isQueued('b')).toBe(true);
    });

    it('should fall back to the default cap for lanes outside every family', () => {
      const scheduler = createScheduler({}, 1, { 'tx-sync:': 2 });
      ['a', 'b'].forEach(id => scheduler.submit(controllableJob(id, 'default').job));

      expect(scheduler.runningCount('default')).toBe(1);
    });
  });

  it('should not start an ineligible job until pump finds it eligible', () => {
    const scheduler = createScheduler();
    let allowed = false;
    const a = controllableJob('a', 'default', () => allowed);
    scheduler.submit(a.job);
    expect(scheduler.isQueued('a')).toBe(true);
    expect(scheduler.isRunning('a')).toBe(false);

    allowed = true;
    scheduler.pump();
    expect(scheduler.isRunning('a')).toBe(true);
  });

  it('should drop a queued job and report it gone', () => {
    const scheduler = createScheduler({ default: 1 });
    const a = controllableJob('a', 'default');
    const b = controllableJob('b', 'default');
    scheduler.submit(a.job);
    scheduler.submit(b.job);
    expect(scheduler.isQueued('b')).toBe(true);

    expect(scheduler.drop('b')).toBe(true);
    expect(scheduler.isQueued('b')).toBe(false);
    expect(scheduler.drop('missing')).toBe(false);
  });

  it('should start the highest-priority eligible job first, FIFO breaking ties', async () => {
    const scheduler = createScheduler({ default: 1 });
    const blocker = controllableJob('blocker', 'default');
    const normal = controllableJob('normal', 'default', () => true, 1);
    const urgent = controllableJob('urgent', 'default', () => true, 2);
    scheduler.submit(blocker.job); // takes the only slot
    scheduler.submit(normal.job); // queued first
    scheduler.submit(urgent.job); // queued second but higher priority

    blocker.finish();
    await flush();

    expect(scheduler.isRunning('urgent')).toBe(true);
    expect(scheduler.isQueued('normal')).toBe(true);
  });

  it('should isolate caps per lane', () => {
    const scheduler = createScheduler({ balances: 1, exchange: 1 });
    scheduler.submit(controllableJob('a1', 'balances').job);
    scheduler.submit(controllableJob('b1', 'exchange').job);
    expect(scheduler.isRunning('a1')).toBe(true);
    expect(scheduler.isRunning('b1')).toBe(true);
  });

  describe('family active-lane caps', () => {
    it('should cap how many lanes of a family run at once', () => {
      // Two accounts per chain, but only two chains live — the shape a pre-submitted tree would
      // otherwise lose, since every account is queued from the start.
      const scheduler = createScheduler({}, 8, { 'tx-sync:': 2 }, { 'tx-sync:': 2 });
      for (const chain of ['eth', 'optimism', 'gnosis', 'base']) {
        for (const n of [1, 2])
          scheduler.submit(controllableJob(`${chain}-${n}`, `tx-sync:${chain}`).job);
      }

      expect(scheduler.runningCount()).toBe(4);
      expect(scheduler.runningCount('tx-sync:eth')).toBe(2);
      expect(scheduler.runningCount('tx-sync:optimism')).toBe(2);
      expect(scheduler.runningCount('tx-sync:gnosis')).toBe(0);
      expect(scheduler.isQueued('gnosis-1')).toBe(true);
    });

    it('should start a queued lane once an active one drains', async () => {
      const scheduler = createScheduler({}, 8, { 'tx-sync:': 1 }, { 'tx-sync:': 1 });
      const eth = controllableJob('eth-1', 'tx-sync:eth');
      const gnosis = controllableJob('gnosis-1', 'tx-sync:gnosis');
      scheduler.submit(eth.job);
      scheduler.submit(gnosis.job);

      expect(scheduler.isRunning('eth-1')).toBe(true);
      expect(scheduler.isQueued('gnosis-1')).toBe(true);

      eth.finish();
      await flush();

      expect(scheduler.isRunning('gnosis-1')).toBe(true);
    });

    it('should let an already active lane keep taking work', () => {
      // The cap is on how many lanes are live, not on the work inside them.
      const scheduler = createScheduler({}, 8, { 'tx-sync:': 3 }, { 'tx-sync:': 1 });
      for (const n of [1, 2, 3])
        scheduler.submit(controllableJob(`eth-${n}`, 'tx-sync:eth').job);

      expect(scheduler.runningCount('tx-sync:eth')).toBe(3);
    });

    it('should not constrain lanes outside a declared family', () => {
      const scheduler = createScheduler({}, 4, { 'tx-sync:': 1 }, { 'tx-sync:': 1 });
      ['a', 'b'].forEach(id => scheduler.submit(controllableJob(id, 'balances').job));

      expect(scheduler.runningCount('balances')).toBe(2);
    });
  });
});
