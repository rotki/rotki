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

  /**
   * Two live jobs may legitimately share an id: cancelling a RUNNING activity settles it terminal
   * while the scheduler still holds its job, and `rerun` then schedules a second under that id.
   * Slot accounting keyed by id collapsed the pair into one entry, so the lane ran over its cap.
   */
  it('should count two live jobs sharing an id as two occupied slots', async () => {
    const scheduler = createScheduler({ decode: 2 }, 4);
    const first = controllableJob('same', 'decode');
    const second = controllableJob('same', 'decode');
    const third = controllableJob('other', 'decode');

    scheduler.submit(first.job);
    scheduler.submit(second.job);
    scheduler.submit(third.job);
    await flush();

    // The cap is 2, and the two same-id jobs already occupy it.
    expect(scheduler.runningCount('decode')).toBe(2);
    expect(scheduler.isQueued('other')).toBe(true);
  });

  it('should not free a slot still held by another job with the same id', async () => {
    const scheduler = createScheduler({ decode: 2 }, 4);
    const first = controllableJob('same', 'decode');
    const second = controllableJob('same', 'decode');
    scheduler.submit(first.job);
    scheduler.submit(second.job);
    await flush();

    first.finish();
    await flush();

    // Only the finished job's slot is released; the second is still running under the same id.
    expect(scheduler.runningCount('decode')).toBe(1);
    expect(scheduler.isRunning('same')).toBe(true);
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

  describe('clear', () => {
    /**
     * A slot is freed from `run()`'s `finally`, and a reset abandons those runs rather than
     * resolving them. Leaving the slots occupied meant a lane stayed full for the life of the
     * process, so the next session's work queued behind jobs belonging to a session that had ended
     * and never started at all.
     */
    it('should free the slots of running jobs, not just the queue', () => {
      const scheduler = createScheduler({ decode: 2 });
      const running = [1, 2].map(n => controllableJob(`old-${n}`, 'decode'));
      running.forEach(({ job }) => scheduler.submit(job));
      // A third job cannot start: the lane is at its cap of 2.
      scheduler.submit(controllableJob('old-3', 'decode').job);
      expect(scheduler.runningCount('decode')).toBe(2);

      // The session ends. The abandoned runs are never resolved.
      scheduler.clear();

      expect(scheduler.runningCount('decode')).toBe(0);
      expect(scheduler.isQueued('old-3')).toBe(false);
    });

    it('should let the next session start work on a lane that was full', () => {
      const scheduler = createScheduler({ decode: 2 });
      const stuck = [1, 2].map(n => controllableJob(`old-${n}`, 'decode'));
      stuck.forEach(({ job }) => scheduler.submit(job));

      scheduler.clear();
      scheduler.submit(controllableJob('new-1', 'decode').job);

      expect(scheduler.isRunning('new-1')).toBe(true);
    });

    it('should ignore an abandoned run settling after the clear', async () => {
      const scheduler = createScheduler({ decode: 2 });
      const old = controllableJob('old-1', 'decode');
      scheduler.submit(old.job);

      scheduler.clear();
      scheduler.submit(controllableJob('new-1', 'decode').job);
      old.finish();
      await flush();

      expect(scheduler.runningCount('decode')).toBe(1);
      expect(scheduler.isRunning('new-1')).toBe(true);
    });
  });
});
