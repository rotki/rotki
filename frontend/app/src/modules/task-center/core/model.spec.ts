import { describe, expect, it } from 'vitest';
import { assembleActivityModel } from './model';
import {
  type Activity,
  type ActivityKind,
  ActivitySourceType,
  type ActivityStatus,
  ActivityKind as Kind,
  makeActivityId,
  ActivityStatus as Status,
} from './types';

const t = (key: string): string => key;

function activity(partial: Partial<Activity> & { kind: ActivityKind; status: ActivityStatus }): Activity {
  return {
    cancellable: false,
    id: makeActivityId(partial.kind, partial.status, partial.startedAt ?? 0),
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    title: partial.kind,
    ...partial,
  };
}

describe('assembleActivityModel', () => {
  it('should return an idle empty model for no activities', () => {
    const model = assembleActivityModel([], t);
    expect(model.groups).toEqual([]);
    expect(model.active).toEqual([]);
    expect(model.pending).toEqual([]);
    expect(model.current).toBeUndefined();
    expect(model.overall).toEqual({ percentage: 0, phase: 'idle' });
  });

  it('should split active (running) and pending and pick current as first running', () => {
    const running = activity({ id: makeActivityId(Kind.TX_SYNC, 'a'), kind: Kind.TX_SYNC, status: Status.RUNNING });
    const pending = activity({ id: makeActivityId(Kind.PRICES, 'b'), kind: Kind.PRICES, status: Status.PENDING });
    const model = assembleActivityModel([pending, running], t);
    expect(model.active).toHaveLength(1);
    expect(model.pending).toHaveLength(1);
    expect(model.current?.id).toBe(running.id);
    expect(model.overall.phase).toBe('working');
  });

  it('should fall back to first pending for current when nothing is running', () => {
    const pending = activity({ id: makeActivityId(Kind.PRICES, 'b'), kind: Kind.PRICES, status: Status.PENDING });
    const model = assembleActivityModel([pending], t);
    expect(model.current?.id).toBe(pending.id);
  });

  it('should order current by kind priority (blockchain-balances before prices)', () => {
    const prices = activity({ id: makeActivityId(Kind.PRICES, 'p'), kind: Kind.PRICES, status: Status.RUNNING });
    const balances = activity({
      id: makeActivityId(Kind.BLOCKCHAIN_BALANCES, 'b'),
      kind: Kind.BLOCKCHAIN_BALANCES,
      status: Status.RUNNING,
    });
    const model = assembleActivityModel([prices, balances], t);
    expect(model.current?.kind).toBe(Kind.BLOCKCHAIN_BALANCES);
    expect(model.groups[0]?.kind).toBe(Kind.BLOCKCHAIN_BALANCES);
  });

  it('should dedupe activities sharing an id keeping the most-live status', () => {
    const id = makeActivityId(Kind.TX_SYNC, 'eth', '0xabc');
    const floor = activity({ id, kind: Kind.TX_SYNC, status: Status.PENDING });
    const native = activity({ id, kind: Kind.TX_SYNC, status: Status.RUNNING });
    const model = assembleActivityModel([floor, native], t);
    const all = model.groups.flatMap(g => g.activities);
    expect(all).toHaveLength(1);
    expect(all[0]?.status).toBe(Status.RUNNING);
  });

  it('should report done phase when every activity is terminal', () => {
    const done = activity({ id: makeActivityId(Kind.PRICES, 'd'), kind: Kind.PRICES, status: Status.COMPLETE });
    const model = assembleActivityModel([done], t);
    expect(model.overall.phase).toBe('done');
  });

  it('should report done, not working, when everything was skipped', () => {
    const skipped = activity({ id: makeActivityId(Kind.TX_SYNC, 's'), kind: Kind.TX_SYNC, status: Status.SKIPPED });
    const model = assembleActivityModel([skipped], t);
    // Skipped is terminal, so the header spinner must not stay up for work that never ran.
    expect(model.overall.phase).toBe('done');
    expect(model.active).toEqual([]);
    expect(model.pending).toEqual([]);
  });

  it('should roll up overall percentage from determinate group percentages', () => {
    const a = activity({ id: makeActivityId(Kind.PRICES, '1'), kind: Kind.PRICES, percentage: 100, status: Status.RUNNING });
    const b = activity({
      id: makeActivityId(Kind.TX_SYNC, '2'),
      kind: Kind.TX_SYNC,
      percentage: 50,
      status: Status.RUNNING,
    });
    const model = assembleActivityModel([a, b], t);
    expect(model.overall.percentage).toBe(75);
  });

  it('should expose the tree, keeping children out of the roots', () => {
    const umbrella = activity({ id: makeActivityId(Kind.HISTORY_SYNC), kind: Kind.HISTORY_SYNC, status: Status.RUNNING });
    const chain = activity({
      id: makeActivityId(Kind.TX_SYNC, 'ethereum'),
      kind: Kind.TX_SYNC,
      parent: umbrella.id,
      status: Status.RUNNING,
    });

    const model = assembleActivityModel([chain, umbrella], t);

    expect(model.roots.map(root => root.id)).toEqual([umbrella.id]);
    expect(model.children.get(umbrella.id)?.map(child => child.id)).toEqual([chain.id]);
  });

  /**
   * The regression: rolling up per-kind groups counted a subtree twice, because an umbrella's
   * percentage is already the mean of its children. Here the umbrella and its three finished
   * children are one job at 100% and the unrelated activity is at 0, so the honest answer is 50.
   * Group-based rollup answered 67 — the same finished work, weighted twice.
   */
  it('should roll up overall from roots only, not once per kind', () => {
    const umbrella = activity({
      id: makeActivityId(Kind.HISTORY_SYNC),
      kind: Kind.HISTORY_SYNC,
      percentage: 100,
      status: Status.RUNNING,
    });
    const children = [1, 2, 3].map(index => activity({
      id: makeActivityId(Kind.TX_SYNC, index),
      kind: Kind.TX_SYNC,
      parent: umbrella.id,
      percentage: 100,
      status: Status.COMPLETE,
    }));
    const unrelated = activity({
      id: makeActivityId(Kind.PRICES, 'latest'),
      kind: Kind.PRICES,
      percentage: 0,
      status: Status.RUNNING,
    });

    const model = assembleActivityModel([umbrella, ...children, unrelated], t);

    expect(model.overall.percentage).toBe(50);
  });
});
