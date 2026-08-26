import type { TaskOrchestrator } from './api';
import { err, isErr, isOk, ok, type Result } from 'plainfp/result';
import { hasTag } from 'plainfp/tagged';
import { assert, describe, expect, it, vi } from 'vitest';
import { BackendCancelled, Cancelled, Skipped, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { INDETERMINATE, isTerminalStatus } from '../status';
import {
  type Activity,
  type ActivityId,
  ActivityKind as Kind,
  makeActivityId,
  makeGroupId,
  ActivityStatus as Status,
} from '../types';
import { createTaskOrchestrator } from './orchestrator';
import { type ActivitySpec, Priority } from './spec';

const flush = async (): Promise<void> => new Promise(resolve => setTimeout(resolve, 0));

interface Controllable {
  spec: ActivitySpec;
  settle: (result: Result<unknown, TaskError>) => void;
  cancelSpy: ReturnType<typeof vi.fn>;
}

function controllable(id: string, overrides: Partial<ActivitySpec> = {}): Controllable {
  let settle!: (result: Result<unknown, TaskError>) => void;
  const promise = new Promise<Result<unknown, TaskError>>((resolve) => {
    settle = resolve;
  });
  const cancelSpy = vi.fn();
  const spec: ActivitySpec = {
    cancel: cancelSpy,
    id: makeActivityId(Kind.OTHER, id),
    kind: Kind.OTHER,
    run: async () => promise,
    title: id,
    ...overrides,
  };
  return { cancelSpy, settle, spec };
}

function byId(orchestrator: TaskOrchestrator, id: ActivityId): Activity | undefined {
  return orchestrator.snapshot().find(activity => activity.id === id);
}

describe('createTaskOrchestrator', () => {
  it('should run a submitted activity immediately and mark it running', () => {
    const orchestrator = createTaskOrchestrator();
    const work = controllable('a');
    const id = orchestrator.submit(work.spec);
    expect(byId(orchestrator, id)?.status).toBe(Status.RUNNING);
  });

  it('should complete on ok and fail on a TaskFailed error', async () => {
    const orchestrator = createTaskOrchestrator();
    const okWork = controllable('ok');
    const failWork = controllable('fail');
    const okId = orchestrator.submit(okWork.spec);
    const failId = orchestrator.submit(failWork.spec);

    okWork.settle({ ok: true, value: 1 });
    failWork.settle({ error: TaskFailed({ message: 'boom' }), ok: false });
    await flush();

    expect(byId(orchestrator, okId)?.status).toBe(Status.COMPLETE);
    expect(byId(orchestrator, okId)?.percentage).toBe(100);
    expect(byId(orchestrator, failId)?.status).toBe(Status.FAILED);
  });

  it('should map cancellation tags to cancelled and other failures to failed', async () => {
    const orchestrator = createTaskOrchestrator();
    const cancelled = controllable('c');
    const backend = controllable('b');
    const failed = controllable('f');
    const cId = orchestrator.submit(cancelled.spec);
    const bId = orchestrator.submit(backend.spec);
    const fId = orchestrator.submit(failed.spec);

    cancelled.settle({ error: Cancelled({ message: 'x' }), ok: false });
    backend.settle({ error: BackendCancelled({ message: 'x' }), ok: false });
    failed.settle({ error: TaskFailed({ message: 'x' }), ok: false });
    await flush();

    expect(byId(orchestrator, cId)?.status).toBe(Status.CANCELLED);
    expect(byId(orchestrator, bId)?.status).toBe(Status.CANCELLED);
    expect(byId(orchestrator, fId)?.status).toBe(Status.FAILED);
  });

  it('should settle a failed outcome at full progress, without marking it fresh', async () => {
    const orchestrator = createTaskOrchestrator();
    const work = controllable('f2');
    const id = orchestrator.submit(work.spec);

    work.settle({ error: TaskFailed({ message: 'network unreachable after retries' }), ok: false });
    await flush();

    const activity = byId(orchestrator, id);
    expect(activity?.status).toBe(Status.FAILED);
    // To an observer a failure is completed *with a failure status*: no further progress is coming,
    // so a bar that excluded it would stall whenever a chain failed.
    expect(activity?.percentage).toBe(100);
    // Freshness is the other axis — it stays stale so a later run retries this one and leaves the
    // siblings that succeeded alone.
    expect(orchestrator.statusOf(Kind.OTHER, 'f2').everCompleted).toBe(false);
  });

  it('should settle a skipped outcome as skipped, at full progress, without marking it fresh', async () => {
    const orchestrator = createTaskOrchestrator();
    const work = controllable('s');
    const id = orchestrator.submit(work.spec);

    work.settle({ error: Skipped({ message: 'disabled in settings' }), ok: false });
    await flush();

    const activity = byId(orchestrator, id);
    expect(activity?.status).toBe(Status.SKIPPED);
    // Counts as done for the bar, so a run with disabled chains still reaches 100%.
    expect(activity?.percentage).toBe(100);
    // But nothing loaded, so re-enabling the work must not read as already fetched.
    expect(orchestrator.statusOf(Kind.OTHER, 's').everCompleted).toBe(false);
  });

  it('should carry the producer reason onto a failed and a skipped activity', async () => {
    const orchestrator = createTaskOrchestrator();
    const failed = controllable('r1');
    const skipped = controllable('r2');
    const failedId = orchestrator.submit(failed.spec);
    const skippedId = orchestrator.submit(skipped.spec);

    failed.settle({ error: TaskFailed({ message: 'network unreachable after retries' }), ok: false });
    skipped.settle({ error: Skipped({ message: 'disabled in settings' }), ok: false });
    await flush();

    // Without this the row renders a bare "Failed"/"Skipped" chip. A skip raises no notification
    // either, so dropping it here drops the reason everywhere.
    expect(byId(orchestrator, failedId)?.reason).toBe('network unreachable after retries');
    expect(byId(orchestrator, skippedId)?.reason).toBe('disabled in settings');
  });

  it('should leave a success and a cancellation without a reason', async () => {
    const orchestrator = createTaskOrchestrator();
    const done = controllable('r3');
    const cancelled = controllable('r4');
    const doneId = orchestrator.submit(done.spec);
    const cancelledId = orchestrator.submit(cancelled.spec);

    done.settle({ ok: true, value: 1 });
    // The user asked for the cancel, so captioning the row with the reason is noise.
    cancelled.settle({ error: Cancelled({ message: 'cancelled by user' }), ok: false });
    await flush();

    expect(byId(orchestrator, doneId)?.reason).toBeUndefined();
    expect(byId(orchestrator, cancelledId)?.reason).toBeUndefined();
  });

  it('should clear a stale reason when a failed activity is rerun', async () => {
    const orchestrator = createTaskOrchestrator();
    const work = controllable('r5', { rerunnable: true });
    const id = orchestrator.submit(work.spec);

    work.settle({ error: TaskFailed({ message: 'network unreachable after retries' }), ok: false });
    await flush();
    expect(byId(orchestrator, id)?.reason).toBe('network unreachable after retries');

    // `rerun` reuses the record, so a reason left behind would caption the new run — and survive it
    // to caption a success.
    orchestrator.rerun(id);
    expect(byId(orchestrator, id)?.reason).toBeUndefined();
  });

  it('should keep an earlier success when work is later skipped', async () => {
    const orchestrator = createTaskOrchestrator();
    const first = controllable('s2');
    orchestrator.submit(first.spec);
    first.settle({ ok: true, value: 1 });
    await flush();

    const second = controllable('s2');
    orchestrator.submit(second.spec);
    second.settle({ error: Skipped({ message: 'disabled in settings' }), ok: false });
    await flush();

    // The data from the earlier run is still there; skipping does not erase freshness.
    expect(orchestrator.statusOf(Kind.OTHER, 's2').everCompleted).toBe(true);
  });

  it('should queue beyond the lane cap and start pending work as slots free', async () => {
    const orchestrator = createTaskOrchestrator({ caps: { default: 2 } });
    const jobs = ['a', 'b', 'c'].map(id => controllable(id));
    const ids = jobs.map(job => orchestrator.submit(job.spec));

    expect(byId(orchestrator, ids[2])?.status).toBe(Status.PENDING);

    jobs[0].settle({ ok: true, value: 1 });
    await flush();

    expect(byId(orchestrator, ids[2])?.status).toBe(Status.RUNNING);
  });

  it('should let a higher-priority queued activity jump ahead when a slot frees', async () => {
    const orchestrator = createTaskOrchestrator({ caps: { default: 1 } });
    const running = controllable('running');
    const normal = controllable('normal', { priority: Priority.NORMAL });
    const urgent = controllable('urgent', { priority: Priority.USER });
    orchestrator.submit(running.spec);
    const normalId = orchestrator.submit(normal.spec);
    const urgentId = orchestrator.submit(urgent.spec);

    running.settle({ ok: true, value: 1 });
    await flush();

    expect(byId(orchestrator, urgentId)?.status).toBe(Status.RUNNING);
    expect(byId(orchestrator, normalId)?.status).toBe(Status.PENDING);
  });

  it('should not start an activity until its dependencies are terminal', async () => {
    const orchestrator = createTaskOrchestrator();
    const first = controllable('first');
    const second = controllable('second', { deps: [makeActivityId(Kind.OTHER, 'first')] });
    const firstId = orchestrator.submit(first.spec);
    const secondId = orchestrator.submit(second.spec);

    expect(byId(orchestrator, secondId)?.status).toBe(Status.PENDING);

    first.settle({ ok: true, value: 1 });
    await flush();

    expect(byId(orchestrator, firstId)?.status).toBe(Status.COMPLETE);
    expect(byId(orchestrator, secondId)?.status).toBe(Status.RUNNING);
  });

  it('should pause background balances while a history sync runs (default rule)', async () => {
    const orchestrator = createTaskOrchestrator();
    const sync = controllable('sync', { id: makeActivityId(Kind.HISTORY_SYNC), kind: Kind.HISTORY_SYNC });
    const balances = controllable('bal', {
      id: makeActivityId(Kind.BLOCKCHAIN_BALANCES, 'eth'),
      kind: Kind.BLOCKCHAIN_BALANCES,
    });
    orchestrator.submit(sync.spec);
    const balId = orchestrator.submit(balances.spec);

    expect(byId(orchestrator, balId)?.status).toBe(Status.PENDING);

    sync.settle({ ok: true, value: 1 });
    await flush();

    expect(byId(orchestrator, balId)?.status).toBe(Status.RUNNING);
  });

  it('should let a user-initiated balance refresh run during a history sync', () => {
    const orchestrator = createTaskOrchestrator();
    const sync = controllable('sync', { id: makeActivityId(Kind.HISTORY_SYNC), kind: Kind.HISTORY_SYNC });
    const balances = controllable('bal', {
      id: makeActivityId(Kind.BLOCKCHAIN_BALANCES, 'eth'),
      kind: Kind.BLOCKCHAIN_BALANCES,
      priority: Priority.USER,
    });
    orchestrator.submit(sync.spec);
    const balId = orchestrator.submit(balances.spec);

    expect(byId(orchestrator, balId)?.status).toBe(Status.RUNNING);
  });

  it('should drop a queued activity on cancel so it never runs', () => {
    const orchestrator = createTaskOrchestrator({ caps: { default: 1 } });
    const running = controllable('run');
    const queued = controllable('queued');
    orchestrator.submit(running.spec);
    const queuedId = orchestrator.submit(queued.spec);

    const result = orchestrator.cancel(queuedId);
    expect(isOk(result)).toBe(true);
    expect(byId(orchestrator, queuedId)?.status).toBe(Status.CANCELLED);
    expect(queued.cancelSpy).not.toHaveBeenCalled();
  });

  it('should abort a running activity via its cancel handle and settle cancelled', async () => {
    const orchestrator = createTaskOrchestrator();
    const work = controllable('a');
    const id = orchestrator.submit(work.spec);

    const result = orchestrator.cancel(id);
    expect(isOk(result)).toBe(true);
    expect(work.cancelSpy).toHaveBeenCalledOnce();

    // even if the task ends up resolving ok, the user-cancel wins
    work.settle({ ok: true, value: 1 });
    await flush();
    expect(byId(orchestrator, id)?.status).toBe(Status.CANCELLED);
  });

  describe('cancelByPrefix', () => {
    it('should cancel every non-terminal activity under the prefix', () => {
      const orchestrator = createTaskOrchestrator();
      const first = controllable('lookup', { id: makeActivityId(Kind.OTHER, 'lookup', 1) });
      const second = controllable('lookup', { id: makeActivityId(Kind.OTHER, 'lookup', 2) });
      orchestrator.submit(first.spec);
      orchestrator.submit(second.spec);

      orchestrator.cancelByPrefix(Kind.OTHER, 'lookup');

      expect(byId(orchestrator, first.spec.id)).toMatchObject({ status: Status.CANCELLED });
      expect(byId(orchestrator, second.spec.id)).toMatchObject({ status: Status.CANCELLED });
    });

    it('should match on a separator boundary and leave unrelated ids running', () => {
      const orchestrator = createTaskOrchestrator();
      const target = controllable('lookup', { id: makeActivityId(Kind.OTHER, 'lookup', 1) });
      const sibling = controllable('other', { id: makeActivityId(Kind.OTHER, 'lookup-extra') });
      orchestrator.submit(target.spec);
      orchestrator.submit(sibling.spec);

      orchestrator.cancelByPrefix(Kind.OTHER, 'lookup');

      expect(byId(orchestrator, target.spec.id)).toMatchObject({ status: Status.CANCELLED });
      expect(byId(orchestrator, sibling.spec.id)).toMatchObject({ status: Status.RUNNING });
      expect(sibling.cancelSpy).not.toHaveBeenCalled();
    });
  });

  describe('cleanup hook', () => {
    it('should run cleanup once when the activity completes', async () => {
      const orchestrator = createTaskOrchestrator();
      const cleanup = vi.fn();
      const work = controllable('a', { cleanup });
      orchestrator.submit(work.spec);

      work.settle({ ok: true, value: 1 });
      await flush();

      expect(cleanup).toHaveBeenCalledOnce();
    });

    it('should run cleanup once even when a running cancel is followed by the run resolving', async () => {
      const orchestrator = createTaskOrchestrator();
      const cleanup = vi.fn();
      const work = controllable('a', { cleanup });
      const id = orchestrator.submit(work.spec);

      orchestrator.cancel(id);
      work.settle({ ok: true, value: 1 });
      await flush();

      expect(cleanup).toHaveBeenCalledOnce();
    });

    it('should run cleanup for an activity cancelled while still queued', () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 1 } });
      const cleanup = vi.fn();
      orchestrator.submit(controllable('run').spec);
      const queuedId = orchestrator.submit(controllable('queued', { cleanup }).spec);

      orchestrator.cancel(queuedId);

      expect(cleanup).toHaveBeenCalledOnce();
    });

    it('should re-arm cleanup on re-run', async () => {
      const orchestrator = createTaskOrchestrator();
      const cleanup = vi.fn();
      const work = controllable('a', { cleanup, rerunnable: true });
      const id = orchestrator.submit(work.spec);

      work.settle({ ok: true, value: 1 });
      await flush();
      expect(cleanup).toHaveBeenCalledOnce();

      // Re-run revives the (already settled) work, which completes again and cleans up a second time.
      orchestrator.rerun(id);
      await flush();
      expect(cleanup).toHaveBeenCalledTimes(2);
    });
  });

  it('should reject cancel of a running activity with no cancel handle', () => {
    const orchestrator = createTaskOrchestrator();
    const work = controllable('a', { cancel: undefined });
    const id = orchestrator.submit(work.spec);
    const result = orchestrator.cancel(id);
    assert(isErr(result));
    expect(hasTag(result.error, 'NotCancellable')).toBe(true);
  });

  it('should reject cancel of unknown and terminal activities', async () => {
    const orchestrator = createTaskOrchestrator();
    const unknown = orchestrator.cancel(makeActivityId(Kind.OTHER, 'nope'));
    assert(isErr(unknown));
    expect(hasTag(unknown.error, 'NotFound')).toBe(true);

    const work = controllable('a');
    const id = orchestrator.submit(work.spec);
    work.settle({ ok: true, value: 1 });
    await flush();
    const terminal = orchestrator.cancel(id);
    assert(isErr(terminal));
    expect(hasTag(terminal.error, 'AlreadyTerminal')).toBe(true);
  });

  it('should cancel every non-terminal activity in a group', () => {
    const orchestrator = createTaskOrchestrator({ caps: { default: 10 } });
    const group = makeGroupId('tx-batch');
    const a = controllable('a', { group });
    const b = controllable('b', { group });
    const other = controllable('c');
    const aId = orchestrator.submit(a.spec);
    const bId = orchestrator.submit(b.spec);
    const cId = orchestrator.submit(other.spec);

    orchestrator.cancelGroup(group);
    expect(byId(orchestrator, aId)?.status).toBe(Status.CANCELLED);
    expect(byId(orchestrator, bId)?.status).toBe(Status.CANCELLED);
    expect(byId(orchestrator, cId)?.status).toBe(Status.RUNNING);
  });

  it('should derive an umbrella percentage from how many children have finished', async () => {
    const orchestrator = createTaskOrchestrator({ caps: { default: 10 } });
    const parent = controllable('umbrella');
    const parentId = orchestrator.submit(parent.spec);

    // An umbrella reports no steps of its own, so until it declares a subtree there is nothing to
    // quantify it by.
    expect(byId(orchestrator, parentId)?.percentage).toBe(INDETERMINATE);

    const children = ['c1', 'c2', 'c3', 'c4'].map((name) => {
      const child = controllable(name, { parent: parentId });
      orchestrator.submit(child.spec);
      return child;
    });

    // Declared but none finished.
    expect(byId(orchestrator, parentId)?.percentage).toBe(0);

    children[0].settle({ ok: true, value: undefined });
    await flush();
    expect(byId(orchestrator, parentId)?.percentage).toBe(25);

    // A failed child is finished work, so it moves the bar exactly like a completed one.
    children[1].settle({ error: TaskFailed({ message: 'boom' }), ok: false });
    await flush();
    expect(byId(orchestrator, parentId)?.percentage).toBe(50);
  });

  it('should leave an activity with no children reporting its own steps', async () => {
    const orchestrator = createTaskOrchestrator({ caps: { default: 10 } });
    let report!: (steps: { current: number; total: number }) => void;
    const id = orchestrator.submit({
      id: makeActivityId(Kind.OTHER, 'lonely'),
      kind: Kind.OTHER,
      run: async (r) => {
        report = r;
        return new Promise<Result<unknown, TaskError>>(() => {});
      },
      title: 'lonely',
    });

    report({ current: 3, total: 4 });
    expect(byId(orchestrator, id)?.percentage).toBe(75);
  });

  it('should report progress as steps and a derived percentage', async () => {
    const orchestrator = createTaskOrchestrator();
    let report!: (steps: { current: number; total: number }) => void;
    const id = orchestrator.submit({
      id: makeActivityId(Kind.PNL_REPORT, 'r'),
      kind: Kind.PNL_REPORT,
      run: async (r) => {
        report = r;
        return new Promise<Result<unknown, TaskError>>(() => {});
      },
      title: 'report',
    });

    report({ current: 1, total: 4 });
    await flush();
    expect(byId(orchestrator, id)?.steps).toEqual({ current: 1, total: 4 });
    expect(byId(orchestrator, id)?.percentage).toBe(25);
  });

  it('should rerun a terminal rerunnable activity and reject otherwise', async () => {
    const orchestrator = createTaskOrchestrator();
    const work = controllable('a', { rerunnable: true });
    const id = orchestrator.submit(work.spec);

    const tooEarly = orchestrator.rerun(id);
    expect(isErr(tooEarly)).toBe(true);

    work.settle({ ok: true, value: 1 });
    await flush();
    expect(byId(orchestrator, id)?.status).toBe(Status.COMPLETE);

    const result = orchestrator.rerun(id);
    expect(isOk(result)).toBe(true);
    expect(byId(orchestrator, id)?.status).toBe(Status.RUNNING);
  });

  it('should notify change listeners and prune terminal activities on clear', async () => {
    const orchestrator = createTaskOrchestrator();
    const listener = vi.fn();
    orchestrator.onChange(listener);
    const work = controllable('a');
    const id = orchestrator.submit(work.spec);
    expect(listener).toHaveBeenCalled();

    work.settle({ ok: true, value: 1 });
    await flush();
    orchestrator.clearTerminal();
    expect(byId(orchestrator, id)).toBeUndefined();
  });

  describe('statusOf and the completion ledger', () => {
    function pricesWork(): Controllable {
      return controllable('prices', { id: makeActivityId(Kind.PRICES), kind: Kind.PRICES });
    }

    it('should report liveness for live records', () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 1 } });
      orchestrator.submit(pricesWork().spec);
      orchestrator.submit(controllable('queued', { id: makeActivityId(Kind.PRICES, 'q'), kind: Kind.PRICES }).spec);

      expect(orchestrator.statusOf(Kind.PRICES)).toMatchObject({
        active: true,
        everCompleted: false,
        pending: true,
        running: true,
      });
    });

    it('should record a success in the ledger with its completion time', async () => {
      let clock = 0;
      const orchestrator = createTaskOrchestrator({ now: () => clock });
      const work = pricesWork();
      orchestrator.submit(work.spec);

      clock = 1000;
      work.settle({ ok: true, value: 1 });
      await flush();

      expect(orchestrator.statusOf(Kind.PRICES)).toMatchObject({
        active: false,
        everCompleted: true,
        lastCompletedAt: 1000,
        lastOutcome: Status.COMPLETE,
      });
    });

    it('should keep a prior success sticky when a later run fails', async () => {
      let clock = 0;
      const orchestrator = createTaskOrchestrator({ now: () => clock });
      const id = makeActivityId(Kind.PRICES);

      const success = controllable('s', { id, kind: Kind.PRICES });
      orchestrator.submit(success.spec);
      clock = 1000;
      success.settle({ ok: true, value: 1 });
      await flush();

      const failure = controllable('f', { id, kind: Kind.PRICES });
      orchestrator.submit(failure.spec);
      clock = 2000;
      failure.settle({ error: TaskFailed({ message: 'boom' }), ok: false });
      await flush();

      expect(orchestrator.statusOf(Kind.PRICES)).toMatchObject({
        everCompleted: true,
        lastCompletedAt: 1000,
        lastOutcome: Status.FAILED,
      });
    });

    it('should keep the ledger when terminal records are pruned', async () => {
      const orchestrator = createTaskOrchestrator();
      const work = pricesWork();
      orchestrator.submit(work.spec);
      work.settle({ ok: true, value: 1 });
      await flush();

      orchestrator.clearTerminal();
      expect(orchestrator.snapshot()).toHaveLength(0);
      expect(orchestrator.statusOf(Kind.PRICES)).toMatchObject({ active: false, everCompleted: true });
    });

    it('should answer per-id status and aggregate over a kind', async () => {
      const orchestrator = createTaskOrchestrator();
      const eth = controllable('eth', { id: makeActivityId(Kind.BLOCKCHAIN_BALANCES, 'eth'), kind: Kind.BLOCKCHAIN_BALANCES });
      const gno = controllable('gno', { id: makeActivityId(Kind.BLOCKCHAIN_BALANCES, 'gno'), kind: Kind.BLOCKCHAIN_BALANCES });
      orchestrator.submit(eth.spec);
      orchestrator.submit(gno.spec);

      eth.settle({ ok: true, value: 1 });
      await flush();

      // aggregate: one chain done, one still running → active and everCompleted both true (partial).
      expect(orchestrator.statusOf(Kind.BLOCKCHAIN_BALANCES)).toMatchObject({ active: true, everCompleted: true, running: true });
      expect(orchestrator.statusOf(Kind.BLOCKCHAIN_BALANCES, 'eth')).toMatchObject({ active: false, everCompleted: true });
      expect(orchestrator.statusOf(Kind.BLOCKCHAIN_BALANCES, 'gno')).toMatchObject({ everCompleted: false, running: true });
    });

    it('should aggregate over a part prefix without matching siblings or a partial name', async () => {
      const orchestrator = createTaskOrchestrator();
      // Two per-request historic fetches plus an unrelated PRICES sibling under another part.
      const btc = controllable('btc', { id: makeActivityId(Kind.PRICES, 'historic', 'BTC', 'USD', 1), kind: Kind.PRICES });
      const eth = controllable('eth', { id: makeActivityId(Kind.PRICES, 'historic', 'ETH', 'USD', 1), kind: Kind.PRICES });
      const rates = controllable('rates', { id: makeActivityId(Kind.PRICES, 'exchange-rates'), kind: Kind.PRICES });
      orchestrator.submit(btc.spec);
      orchestrator.submit(eth.spec);
      orchestrator.submit(rates.spec);

      btc.settle({ ok: true, value: 1 });
      await flush();

      // The coarse read the spinner sites use: one historic fetch still in flight.
      expect(orchestrator.statusOfPrefix(Kind.PRICES, 'historic')).toMatchObject({
        active: true,
        everCompleted: true,
        running: true,
      });

      // Exact-id lookups still resolve each request independently.
      expect(orchestrator.statusOf(Kind.PRICES, 'historic', 'BTC', 'USD', 1)).toMatchObject({ active: false, everCompleted: true });
      expect(orchestrator.statusOf(Kind.PRICES, 'historic', 'ETH', 'USD', 1)).toMatchObject({ everCompleted: false, running: true });

      // A sibling part is not swept in by the prefix.
      eth.settle({ ok: true, value: 1 });
      await flush();
      expect(orchestrator.statusOfPrefix(Kind.PRICES, 'historic')).toMatchObject({ active: false, running: false });
      expect(orchestrator.statusOfPrefix(Kind.PRICES, 'exchange-rates')).toMatchObject({ active: true, running: true });
    });

    it('should not let a prefix match a longer part name on a non-separator boundary', async () => {
      const orchestrator = createTaskOrchestrator();
      const other = controllable('hist', { id: makeActivityId(Kind.PRICES, 'historical-daily'), kind: Kind.PRICES });
      orchestrator.submit(other.spec);
      await flush();

      // `prices:historic` must not match `prices:historical-daily`.
      expect(orchestrator.statusOfPrefix(Kind.PRICES, 'historic')).toMatchObject({ active: false, running: false });
      expect(orchestrator.statusOfPrefix(Kind.PRICES, 'historical-daily')).toMatchObject({ active: true, running: true });
    });

    it('should record a completion for data that arrived without work', () => {
      const orchestrator = createTaskOrchestrator({ now: () => 1000 });
      const listener = vi.fn();
      orchestrator.onChange(listener);

      orchestrator.markCompleted(Kind.BLOCKCHAIN_BALANCES, 'eth');

      // No activity was ever submitted, so the id reads as loaded but never as live.
      expect(orchestrator.snapshot()).toHaveLength(0);
      expect(orchestrator.statusOf(Kind.BLOCKCHAIN_BALANCES, 'eth')).toMatchObject({
        active: false,
        everCompleted: true,
        lastCompletedAt: 1000,
        lastOutcome: Status.COMPLETE,
      });
      expect(listener).toHaveBeenCalledOnce();
    });

    it('should let a real run overwrite a marked completion', async () => {
      let clock = 1000;
      const orchestrator = createTaskOrchestrator({ now: () => clock });
      orchestrator.markCompleted(Kind.PRICES);

      const work = pricesWork();
      orchestrator.submit(work.spec);
      clock = 2000;
      work.settle({ error: TaskFailed({ message: 'boom' }), ok: false });
      await flush();

      // The marked success stays sticky under `lastSuccessAt`, exactly as a real earlier success would.
      expect(orchestrator.statusOf(Kind.PRICES)).toMatchObject({
        everCompleted: true,
        lastCompletedAt: 1000,
        lastOutcome: Status.FAILED,
      });
    });

    it('should drop recorded completions under a prefix on invalidate', async () => {
      const orchestrator = createTaskOrchestrator();
      const eth = controllable('eth', { id: makeActivityId(Kind.BLOCKCHAIN_BALANCES, 'eth'), kind: Kind.BLOCKCHAIN_BALANCES });
      const gno = controllable('gno', { id: makeActivityId(Kind.BLOCKCHAIN_BALANCES, 'gno'), kind: Kind.BLOCKCHAIN_BALANCES });
      orchestrator.submit(eth.spec);
      orchestrator.submit(gno.spec);
      eth.settle({ ok: true, value: 1 });
      gno.settle({ ok: true, value: 1 });
      await flush();

      orchestrator.invalidate(Kind.BLOCKCHAIN_BALANCES, 'eth');

      expect(orchestrator.statusOf(Kind.BLOCKCHAIN_BALANCES, 'eth').everCompleted).toBe(false);
      expect(orchestrator.statusOf(Kind.BLOCKCHAIN_BALANCES, 'gno').everCompleted).toBe(true);

      orchestrator.invalidate(Kind.BLOCKCHAIN_BALANCES);
      expect(orchestrator.statusOf(Kind.BLOCKCHAIN_BALANCES, 'gno').everCompleted).toBe(false);
    });

    it('should leave an in-flight activity running when its freshness is invalidated', async () => {
      const orchestrator = createTaskOrchestrator();
      const work = pricesWork();
      orchestrator.submit(work.spec);

      orchestrator.invalidate(Kind.PRICES);
      expect(orchestrator.statusOf(Kind.PRICES)).toMatchObject({ everCompleted: false, running: true });

      // The run that was already going still writes a fresh entry when it settles.
      work.settle({ ok: true, value: 1 });
      await flush();
      expect(orchestrator.statusOf(Kind.PRICES)).toMatchObject({ everCompleted: true, running: false });
    });

    it('should not emit when invalidate matches nothing', () => {
      const orchestrator = createTaskOrchestrator();
      const listener = vi.fn();
      orchestrator.onChange(listener);

      orchestrator.invalidate(Kind.PRICES);
      expect(listener).not.toHaveBeenCalled();
    });

    it('should wipe live records and the ledger on reset', async () => {
      const orchestrator = createTaskOrchestrator();
      const work = pricesWork();
      orchestrator.submit(work.spec);
      work.settle({ ok: true, value: 1 });
      await flush();

      orchestrator.reset();
      expect(orchestrator.snapshot()).toHaveLength(0);
      expect(orchestrator.statusOf(Kind.PRICES)).toMatchObject({ active: false, everCompleted: false, pending: false, running: false });
    });
  });

  describe('staleAfter edges', () => {
    /** A consumer that has loaded once, so its freshness is there to be dropped. */
    async function loadedConsumer(orchestrator: TaskOrchestrator, staleAfter: ActivitySpec['staleAfter']): Promise<void> {
      const consumer = controllable('consumer', { kind: Kind.NFT_BALANCES, id: makeActivityId(Kind.NFT_BALANCES), staleAfter });
      orchestrator.submit(consumer.spec);
      consumer.settle(ok(undefined));
      await flush();
      assert(orchestrator.statusOf(Kind.NFT_BALANCES).everCompleted);
    }

    it('should drop the consumer freshness when a matching producer completes', async () => {
      const orchestrator = createTaskOrchestrator();
      await loadedConsumer(orchestrator, [{ kind: Kind.PURGE, parts: ['transactions'] }]);

      const producer = controllable('purge', { kind: Kind.PURGE, id: makeActivityId(Kind.PURGE, 'transactions') });
      orchestrator.submit(producer.spec);
      producer.settle(ok(undefined));
      await flush();

      // The effect is what matters: the next guarded fetch is admitted again.
      expect(orchestrator.statusOf(Kind.NFT_BALANCES).everCompleted).toBe(false);
    });

    it('should match a producer whose id extends the declared parts', async () => {
      const orchestrator = createTaskOrchestrator();
      await loadedConsumer(orchestrator, [{ kind: Kind.PURGE, parts: ['transactions'] }]);

      const producer = controllable('purge', { kind: Kind.PURGE, id: makeActivityId(Kind.PURGE, 'transactions', 'eth') });
      orchestrator.submit(producer.spec);
      producer.settle(ok(undefined));
      await flush();

      expect(orchestrator.statusOf(Kind.NFT_BALANCES).everCompleted).toBe(false);
    });

    it('should leave the consumer fresh when another source is purged', async () => {
      const orchestrator = createTaskOrchestrator();
      await loadedConsumer(orchestrator, [{ kind: Kind.PURGE, parts: ['transactions'] }]);

      const producer = controllable('purge', { kind: Kind.PURGE, id: makeActivityId(Kind.PURGE, 'defi_modules') });
      orchestrator.submit(producer.spec);
      producer.settle(ok(undefined));
      await flush();

      expect(orchestrator.statusOf(Kind.NFT_BALANCES).everCompleted).toBe(true);
    });

    it('should leave the consumer fresh when the producer fails', async () => {
      const orchestrator = createTaskOrchestrator();
      await loadedConsumer(orchestrator, [{ kind: Kind.PURGE, parts: ['transactions'] }]);

      const producer = controllable('purge', { kind: Kind.PURGE, id: makeActivityId(Kind.PURGE, 'transactions') });
      orchestrator.submit(producer.spec);
      producer.settle(err(TaskFailed({ message: 'nope' })));
      await flush();

      // Nothing was deleted, so what derives from it is still good.
      expect(orchestrator.statusOf(Kind.NFT_BALANCES).everCompleted).toBe(true);
    });

    it('should match every activity of the kind when no parts are declared', async () => {
      const orchestrator = createTaskOrchestrator();
      await loadedConsumer(orchestrator, [{ kind: Kind.PURGE }]);

      const producer = controllable('purge', { kind: Kind.PURGE, id: makeActivityId(Kind.PURGE, 'anything') });
      orchestrator.submit(producer.spec);
      producer.settle(ok(undefined));
      await flush();

      expect(orchestrator.statusOf(Kind.NFT_BALANCES).everCompleted).toBe(false);
    });

    it('should not let a consumer invalidate itself', async () => {
      const orchestrator = createTaskOrchestrator();
      // Declares an edge against its own kind — its own completion must still count as fresh.
      await loadedConsumer(orchestrator, [{ kind: Kind.NFT_BALANCES }]);

      expect(orchestrator.statusOf(Kind.NFT_BALANCES).everCompleted).toBe(true);
    });
  });

  describe('parent gating', () => {
    it('should hold a child until its parent starts', async () => {
      // The parent's lane is full, so it cannot start — and neither may its child, even though the
      // child's own lane is free. Without this a pre-submitted tree runs bottom-up.
      const orchestrator = createTaskOrchestrator({ caps: { 'chain-sync': 1 } });
      const first = controllable('first', { id: makeActivityId(Kind.TX_SYNC, 'eth'), kind: Kind.TX_SYNC, lane: 'chain-sync' });
      const parent = controllable('second', { id: makeActivityId(Kind.TX_SYNC, 'gnosis'), kind: Kind.TX_SYNC, lane: 'chain-sync' });
      orchestrator.submit(first.spec);
      orchestrator.submit(parent.spec);

      const child = controllable('child', {
        id: makeActivityId(Kind.TX_SYNC, 'gnosis', '0xabc'),
        kind: Kind.TX_SYNC,
        parent: parent.spec.id,
      });
      orchestrator.submit(child.spec);
      await flush();

      expect(byId(orchestrator, parent.spec.id)?.status).toBe(Status.PENDING);
      expect(byId(orchestrator, child.spec.id)?.status).toBe(Status.PENDING);

      // Freeing the parent's lane starts the parent, which in turn unblocks the child.
      first.settle(ok(undefined));
      await flush();

      expect(byId(orchestrator, parent.spec.id)?.status).toBe(Status.RUNNING);
      expect(byId(orchestrator, child.spec.id)?.status).toBe(Status.RUNNING);
    });

    /**
     * The chain-job shape, against the real scheduler. A parent that *awaits its own children*
     * holds its lane slot for the whole body, so the children must not need a slot on that lane —
     * with a cap of 2, two such parents would wait forever on work that can never start.
     *
     * This is why token detection has its own `detect:<chain>` family instead of sharing
     * `BALANCES_LANE` with the chain job. Nothing above the orchestrator can catch it: every
     * producer spec stubs `submitTask` to run inline, where lanes do not exist.
     */
    it('should let a parent awaiting children hold its lane without deadlocking them', async () => {
      // Two balances slots, both taken by the chain jobs; the detect family has room of its own.
      const orchestrator = createTaskOrchestrator({ caps: { balances: 2 }, defaultCap: 4 });
      const children = new Map<ActivityId, Controllable>();

      /** Resolves when that activity reaches a terminal status — the parent's real await. */
      const awaitTerminal = async (id: ActivityId): Promise<void> => new Promise<void>((resolve) => {
        const stop = orchestrator.onChange(() => {
          const activity = byId(orchestrator, id);
          if (activity && isTerminalStatus(activity.status)) {
            stop();
            resolve();
          }
        });
      });

      const chainJob = (chain: string): ActivitySpec => ({
        cancel: vi.fn(),
        id: makeActivityId(Kind.BLOCKCHAIN_BALANCES, chain),
        kind: Kind.BLOCKCHAIN_BALANCES,
        lane: 'balances',
        run: async (): Promise<Result<unknown, TaskError>> => {
          const ids = ['0xaaa', '0xbbb'].map((address) => {
            const child = controllable(`${chain}-${address}`, {
              id: makeActivityId(Kind.TOKEN_DETECTION, chain, address),
              kind: Kind.TOKEN_DETECTION,
              lane: `detect:${chain}`,
              parent: makeActivityId(Kind.BLOCKCHAIN_BALANCES, chain),
            });
            children.set(child.spec.id, child);
            orchestrator.submit(child.spec);
            return child.spec.id;
          });
          await Promise.all(ids.map(awaitTerminal));
          return ok(undefined);
        },
        title: chain,
      });

      orchestrator.submit(chainJob('eth'));
      orchestrator.submit(chainJob('gnosis'));
      await vi.waitFor(() => {
        expect(children.size).toBe(4);
      });

      // The assertion that fails if detection shares the balances lane: with both slots held by
      // the parents, every child would still be PENDING here and nothing could ever settle them.
      for (const child of children.values()) {
        expect(byId(orchestrator, child.spec.id)?.status).toBe(Status.RUNNING);
        child.settle(ok(undefined));
      }

      await vi.waitFor(() => {
        expect(byId(orchestrator, makeActivityId(Kind.BLOCKCHAIN_BALANCES, 'eth'))?.status).toBe(Status.COMPLETE);
        expect(byId(orchestrator, makeActivityId(Kind.BLOCKCHAIN_BALANCES, 'gnosis'))?.status).toBe(Status.COMPLETE);
      });
    });

    it('should not gate a child whose parent is unknown', async () => {
      const orchestrator = createTaskOrchestrator();
      const child = controllable('orphan', { parent: makeActivityId(Kind.TX_SYNC, 'never-submitted') });
      orchestrator.submit(child.spec);
      await flush();

      expect(byId(orchestrator, child.spec.id)?.status).toBe(Status.RUNNING);
    });
  });

  describe('container activities', () => {
    /**
     * A fan-out umbrella settles COMPLETE whenever its children settle — `allSettled`, on
     * purpose, because a failure belongs to the subject that failed. Sharing its children's kind
     * then wrote a *success* to the completion ledger even when every child FAILED, and
     * `statusOf(kind)` aggregates by kind: the dashboard read "loaded" after a total failure.
     */
    it('should not let a container claim freshness for its kind', async () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 10 } });
      const umbrella = controllable('run', { container: true });
      const child = controllable('subject', { parent: umbrella.spec.id });
      orchestrator.submit(umbrella.spec);
      orchestrator.submit(child.spec);

      // Every subject fails; the container completes anyway, as a container does.
      child.settle(err(TaskFailed({ message: 'backend unreachable' })));
      umbrella.settle(ok(undefined));
      await flush();

      expect(byId(orchestrator, umbrella.spec.id)?.status).toBe(Status.COMPLETE);
      expect(orchestrator.statusOf(Kind.OTHER).everCompleted).toBe(false);
    });

    it('should still let a non-container umbrella record its own completion', async () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 10 } });
      const umbrella = controllable('run-subject');
      orchestrator.submit(umbrella.spec);

      umbrella.settle(ok(undefined));
      await flush();

      // `HISTORY_SYNC`'s umbrella *is* the subject for its kind, and its entry is load-bearing.
      expect(orchestrator.statusOf(Kind.OTHER).everCompleted).toBe(true);
    });
  });

  describe('cancel cascade', () => {
    /** An umbrella, one chain under it, two accounts under the chain — the history-refresh shape. */
    function tree(orchestrator: TaskOrchestrator): {
      root: Controllable;
      chain: Controllable;
      accounts: [Controllable, Controllable];
    } {
      const root = controllable('umbrella');
      orchestrator.submit(root.spec);
      const chain = controllable('chain', { parent: root.spec.id });
      orchestrator.submit(chain.spec);
      const accounts: [Controllable, Controllable] = [
        controllable('0xaaa', { parent: chain.spec.id }),
        controllable('0xbbb', { parent: chain.spec.id }),
      ];
      for (const account of accounts)
        orchestrator.submit(account.spec);

      return { accounts, chain, root };
    }

    /**
     * The bug this package exists for. Every native spec carries a cancel handle, so cancelling
     * a parent always "succeeded" — but the handle only aborts that activity's own backend task,
     * which an umbrella never has. The row settled CANCELLED and vanished while the whole subtree
     * carried on working.
     */
    it('should cancel every descendant, not just the row', async () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 10 } });
      const { accounts, chain, root } = tree(orchestrator);
      await flush();

      orchestrator.cancel(root.spec.id);
      await flush();

      expect(byId(orchestrator, root.spec.id)?.status).toBe(Status.CANCELLED);
      expect(byId(orchestrator, chain.spec.id)?.status).toBe(Status.CANCELLED);
      for (const account of accounts)
        expect(byId(orchestrator, account.spec.id)?.status).toBe(Status.CANCELLED);
    });

    /** The handle is what actually stops the backend task, so every live node's must fire. */
    it('should fire each descendant\'s cancel handle', async () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 10 } });
      const { accounts, chain, root } = tree(orchestrator);
      await flush();

      orchestrator.cancel(root.spec.id);

      expect(chain.cancelSpy).toHaveBeenCalledOnce();
      for (const account of accounts)
        expect(account.cancelSpy).toHaveBeenCalledOnce();
    });

    /**
     * `eligible` only refused a child whose parent was still PENDING, so a queued child of a
     * cancelled parent started the moment a lane freed up — the cancel bought nothing.
     */
    it('should not start a queued child after its parent is cancelled', async () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 1 } });
      const blocker = controllable('blocker');
      orchestrator.submit(blocker.spec);
      const parent = controllable('parent');
      orchestrator.submit(parent.spec);
      const child = controllable('child', { parent: parent.spec.id });
      orchestrator.submit(child.spec);
      await flush();

      expect(byId(orchestrator, child.spec.id)?.status).toBe(Status.PENDING);

      orchestrator.cancel(parent.spec.id);
      // Frees the only lane, which is what would let an orphaned child through.
      blocker.settle(ok(undefined));
      await flush();

      expect(byId(orchestrator, child.spec.id)?.status).toBe(Status.CANCELLED);
    });

    /**
     * The wedge `eligible` alone would create. A child submitted after its parent ended can
     * never become eligible, so leaving it PENDING would hold its caller's await open for the life
     * of the process. It has to be *settled*, not merely refused.
     */
    it('should settle a child submitted after its parent was cancelled', async () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 10 } });
      const parent = controllable('parent');
      orchestrator.submit(parent.spec);
      await flush();
      orchestrator.cancel(parent.spec.id);

      const late = controllable('late', { parent: parent.spec.id });
      orchestrator.submit(late.spec);
      await flush();

      expect(byId(orchestrator, late.spec.id)?.status).toBe(Status.CANCELLED);
    });

    /**
     * The reason no new cancel handle is needed anywhere: a parent whose body awaits its
     * children resolves on its own once they settle, and `cancelRequested` maps that outcome to
     * CANCELLED however the body chose to return.
     */
    it('should keep a parent cancelled when its own body later settles ok', async () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 10 } });
      const { root } = tree(orchestrator);
      await flush();

      orchestrator.cancel(root.spec.id);
      root.settle(ok(undefined));
      await flush();

      expect(byId(orchestrator, root.spec.id)?.status).toBe(Status.CANCELLED);
    });

    /** Cancelling a chain must not touch its siblings, or "stop this chain" stops the refresh. */
    it('should leave a sibling subtree running', async () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 10 } });
      const root = controllable('umbrella');
      orchestrator.submit(root.spec);
      const doomed = controllable('doomed', { parent: root.spec.id });
      const survivor = controllable('survivor', { parent: root.spec.id });
      orchestrator.submit(doomed.spec);
      orchestrator.submit(survivor.spec);
      const doomedChild = controllable('doomed-child', { parent: doomed.spec.id });
      const survivorChild = controllable('survivor-child', { parent: survivor.spec.id });
      orchestrator.submit(doomedChild.spec);
      orchestrator.submit(survivorChild.spec);
      await flush();

      orchestrator.cancel(doomed.spec.id);
      await flush();

      expect(byId(orchestrator, doomedChild.spec.id)?.status).toBe(Status.CANCELLED);
      expect(byId(orchestrator, survivor.spec.id)?.status).toBe(Status.RUNNING);
      expect(byId(orchestrator, survivorChild.spec.id)?.status).toBe(Status.RUNNING);
      expect(byId(orchestrator, root.spec.id)?.status).toBe(Status.RUNNING);
    });

    /**
     * The case an `eligible` guard could not have handled. `cancel` never runs here, so a
     * cascade hung off cancellation would leave these children queued — and refusing them in
     * `eligible` instead would wedge them PENDING for the life of the process, since nothing would
     * ever settle them. Hanging the walk off the settle is what makes one rule cover both.
     */
    it('should cancel the subtree when a parent fails rather than being cancelled', async () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 1 } });
      const blocker = controllable('blocker');
      orchestrator.submit(blocker.spec);
      const parent = controllable('parent');
      orchestrator.submit(parent.spec);
      const child = controllable('child', { parent: parent.spec.id });
      orchestrator.submit(child.spec);
      await flush();

      // The parent reaches a terminal FAILED while its child is still queued behind the cap.
      blocker.settle(ok(undefined));
      await flush();
      parent.settle(err(TaskFailed({ message: 'boom' })));
      await flush();

      expect(byId(orchestrator, parent.spec.id)?.status).toBe(Status.FAILED);
      expect(byId(orchestrator, child.spec.id)?.status).toBe(Status.CANCELLED);
    });

    /** Same rule, the skipped flavour: a chain with nothing to do has no work beneath it either. */
    it('should cancel the subtree when a parent is skipped', async () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 1 } });
      const blocker = controllable('blocker');
      orchestrator.submit(blocker.spec);
      const parent = controllable('parent');
      orchestrator.submit(parent.spec);
      const child = controllable('child', { parent: parent.spec.id });
      orchestrator.submit(child.spec);
      await flush();

      blocker.settle(ok(undefined));
      await flush();
      parent.settle(err(Skipped({ message: 'nothing to do' })));
      await flush();

      expect(byId(orchestrator, parent.spec.id)?.status).toBe(Status.SKIPPED);
      expect(byId(orchestrator, child.spec.id)?.status).toBe(Status.CANCELLED);
    });

    /** A parent that finishes normally must leave its subtree alone. */
    it('should not touch the subtree when a parent completes', async () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 10 } });
      const { accounts, chain, root } = tree(orchestrator);
      await flush();

      root.settle(ok(undefined));
      await flush();

      expect(byId(orchestrator, root.spec.id)?.status).toBe(Status.COMPLETE);
      expect(byId(orchestrator, chain.spec.id)?.status).toBe(Status.RUNNING);
      for (const account of accounts)
        expect(byId(orchestrator, account.spec.id)?.status).toBe(Status.RUNNING);
    });

    /** A producer's malformed parent chain is not a reason to hang the orchestrator. */
    it('should terminate on a parent cycle', async () => {
      const orchestrator = createTaskOrchestrator({ caps: { default: 10 } });
      const a = controllable('a');
      orchestrator.submit(a.spec);
      const b = controllable('b', { parent: a.spec.id });
      orchestrator.submit(b.spec);
      // `a` is re-submitted pointing at its own descendant, closing the loop.
      orchestrator.submit({ ...a.spec, parent: b.spec.id });
      await flush();

      orchestrator.cancel(a.spec.id);

      expect(byId(orchestrator, b.spec.id)?.status).toBe(Status.CANCELLED);
    });
  });

  describe('superseded records', () => {
    /**
     * `submitTask` resolves its caller a tick before the run reaches `settleTerminal`, so a caller
     * that awaits and immediately re-submits the same id (the price-refresh queue walks its work
     * with exactly that shape) replaces the record while the old run is still in flight. Guarding
     * on the presence of the id rather than on record identity let the old run write a COMPLETE
     * ledger entry for the *new* activity — `everCompleted` read true for work barely started.
     */
    it('should not let a superseded run complete the record that replaced it', async () => {
      const orchestrator = createTaskOrchestrator();
      const first = controllable('shared');
      orchestrator.submit(first.spec);
      await flush();

      const second = controllable('shared');
      orchestrator.submit(second.spec);
      await flush();

      first.settle(ok(undefined));
      await flush();

      expect(orchestrator.statusOf(Kind.OTHER, 'shared')).toMatchObject({
        everCompleted: false,
        running: true,
      });
    });

    /**
     * The identity guard stops the abandoned run from settling, which would also stop its
     * `cleanup` from ever firing — trading a corrupted ledger for a leaked producer resource. It
     * is released at the point of supersession instead, and exactly once.
     */
    it('should release the superseded run once when its id is re-submitted', async () => {
      const orchestrator = createTaskOrchestrator();
      const cleanup = vi.fn();
      const first = controllable('shared', { cleanup });
      orchestrator.submit(first.spec);
      await flush();

      const second = controllable('shared');
      orchestrator.submit(second.spec);
      await flush();

      expect(cleanup).toHaveBeenCalledOnce();

      // The abandoned run resolving later must not fire it a second time.
      first.settle(ok(undefined));
      await flush();

      expect(cleanup).toHaveBeenCalledOnce();
      expect(byId(orchestrator, second.spec.id)?.status).toBe(Status.RUNNING);
    });
  });

  describe('reset', () => {
    /**
     * Clearing `records` first made `settleTerminal` return at its identity guard when the
     * abandoned run resolved, so producer teardown never fired: a P&L report generated across a
     * logout kept polling `getProgress()` for a session that had ended.
     */
    it('should run cleanup for live activities on reset', async () => {
      const orchestrator = createTaskOrchestrator();
      const cleanup = vi.fn();
      const live = controllable('live', { cleanup });
      orchestrator.submit(live.spec);
      await flush();

      orchestrator.reset();

      expect(cleanup).toHaveBeenCalledOnce();
    });

    it('should not run cleanup twice when the abandoned run settles after reset', async () => {
      const orchestrator = createTaskOrchestrator();
      const cleanup = vi.fn();
      const live = controllable('live', { cleanup });
      orchestrator.submit(live.spec);
      await flush();

      orchestrator.reset();
      live.settle(ok(undefined));
      await flush();

      expect(cleanup).toHaveBeenCalledOnce();
    });
  });
});
