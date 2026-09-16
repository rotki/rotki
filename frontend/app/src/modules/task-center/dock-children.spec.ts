import { describe, expect, it } from 'vitest';
import { type Activity, ActivityKind, ActivitySourceType, ActivityStatus, makeActivityId } from './core/types';
import { arrangeChildren, type DockChildEntry } from './dock-children';

function chain(name: string, status: ActivityStatus, reason?: string): Activity {
  return {
    cancellable: false,
    id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, name),
    kind: ActivityKind.BLOCKCHAIN_BALANCES,
    percentage: -1,
    reason,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status,
    title: name,
  };
}

const NO_ACCOUNTS = 'No tracked accounts on this chain';
const leaf = (): boolean => true;

function describeEntries(entries: DockChildEntry[]): string[] {
  return entries.map(entry => (entry.type === 'node' ? entry.activity.title : `skipped[${entry.activities.map(a => a.title).join(',')}]`));
}

describe('arrangeChildren', () => {
  const children = [
    chain('eth', ActivityStatus.COMPLETE),
    chain('bch', ActivityStatus.SKIPPED, NO_ACCOUNTS),
    chain('eth2', ActivityStatus.FAILED, 'unreachable'),
    chain('ksm', ActivityStatus.SKIPPED, NO_ACCOUNTS),
    chain('btc', ActivityStatus.COMPLETE),
    chain('sonic', ActivityStatus.SKIPPED, 'disabled in settings'),
  ];

  it('should keep start order, with no grouping, while the job runs', () => {
    expect(describeEntries(arrangeChildren(children, false, leaf))).toEqual(['eth', 'bch', 'eth2', 'ksm', 'btc', 'sonic']);
  });

  it('should sort a settled job\'s children failed, then skipped, then done, keeping start order within each', () => {
    const entries = arrangeChildren(children, true, () => false);

    expect(describeEntries(entries)).toEqual(['eth2', 'bch', 'ksm', 'sonic', 'eth', 'btc']);
  });

  it('should fold skipped leaves that share a reason into one entry, where the first of them sorted', () => {
    const entries = arrangeChildren(children, true, leaf);

    expect(describeEntries(entries)).toEqual(['eth2', 'skipped[bch,ksm]', 'sonic', 'eth', 'btc']);
    const group = entries[1];
    expect(group?.type === 'skipped' ? group.reason : undefined).toBe(NO_ACCOUNTS);
  });

  it('should leave a skipped child that has children of its own as a row, never folded', () => {
    const entries = arrangeChildren(children, true, activity => activity.title !== 'ksm');

    expect(describeEntries(entries)).toEqual(['eth2', 'bch', 'ksm', 'sonic', 'eth', 'btc']);
  });
});
