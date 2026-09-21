import { describe, expect, it } from 'vitest';
import {
  type Activity,
  ActivityPart,
  ActivitySourceType,
  ActivityKind as Kind,
  makeActivityId,
  ActivityStatus as Status,
  WaitingReason,
} from '../types';
import { type EligibilityRule, excludeMatchingDuringReset, firstRuleHold, pauseBalancesDuringHistorySync } from './rules';
import { Priority } from './spec';

function activity(overrides: Partial<Activity> & Pick<Activity, 'id' | 'kind' | 'status'>): Activity {
  return {
    cancellable: false,
    percentage: 0,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    title: 'work',
    ...overrides,
  };
}

function matching(status: Activity['status']): Activity {
  return activity({
    id: makeActivityId(Kind.HISTORY_EVENTS, ActivityPart.MATCH),
    kind: Kind.HISTORY_EVENTS,
    status,
  });
}

function bridgeMatching(status: Activity['status']): Activity {
  return activity({
    id: makeActivityId(Kind.HISTORY_EVENTS, ActivityPart.BRIDGE),
    kind: Kind.HISTORY_EVENTS,
    status,
  });
}

function reset(status: Activity['status']): Activity {
  return activity({
    id: makeActivityId(Kind.REDECODE, 'all'),
    kind: Kind.REDECODE,
    resets: true,
    status,
  });
}

function historySync(status: Activity['status']): Activity {
  return activity({ id: makeActivityId(Kind.HISTORY_SYNC), kind: Kind.HISTORY_SYNC, status });
}

function balances(priority?: number): Activity {
  return activity({
    id: makeActivityId(Kind.BLOCKCHAIN_BALANCES, 'eth'),
    kind: Kind.BLOCKCHAIN_BALANCES,
    priority,
    status: Status.PENDING,
  });
}

describe('pauseBalancesDuringHistorySync', () => {
  it('should hold a background balance query back while a sync is running, naming the sync', () => {
    const candidate = balances();
    const sync = historySync(Status.RUNNING);
    expect(pauseBalancesDuringHistorySync(candidate, [candidate, sync])).toEqual({ on: sync.id, reason: WaitingReason.HISTORY_SYNC });
  });

  it('should let a background balance query run once the sync has settled', () => {
    const candidate = balances();
    expect(pauseBalancesDuringHistorySync(candidate, [candidate, historySync(Status.COMPLETE)])).toBeUndefined();
  });

  it('should ignore a sync that is only queued', () => {
    const candidate = balances();
    expect(pauseBalancesDuringHistorySync(candidate, [candidate, historySync(Status.PENDING)])).toBeUndefined();
  });

  it('should let a user-initiated balance query through', () => {
    const candidate = balances(Priority.USER);
    expect(pauseBalancesDuringHistorySync(candidate, [candidate, historySync(Status.RUNNING)])).toBeUndefined();
  });

  it('should ignore non-balance candidates', () => {
    const candidate = activity({ id: makeActivityId(Kind.TX_SYNC, 'eth'), kind: Kind.TX_SYNC, status: Status.PENDING });
    expect(pauseBalancesDuringHistorySync(candidate, [candidate, historySync(Status.RUNNING)])).toBeUndefined();
  });
});

describe('excludeMatchingDuringReset', () => {
  it('should hold matching back while a reset is running, naming the reset', () => {
    const candidate = matching(Status.PENDING);
    const redecode = reset(Status.RUNNING);
    expect(excludeMatchingDuringReset(candidate, [candidate, redecode])).toEqual({ on: redecode.id, reason: WaitingReason.REDECODE });
  });

  it('should hold matching back while a reset is merely queued, or a stream of matching work starves it', () => {
    const candidate = matching(Status.PENDING);
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.PENDING)])).toMatchObject({ reason: WaitingReason.REDECODE });
  });

  it('should cover bridge matching as well as asset-movement matching', () => {
    const candidate = bridgeMatching(Status.PENDING);
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.RUNNING)])).toMatchObject({ reason: WaitingReason.REDECODE });
  });

  it('should let matching run once the reset has settled', () => {
    const candidate = matching(Status.PENDING);
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.COMPLETE)])).toBeUndefined();
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.FAILED)])).toBeUndefined();
  });

  it('should hold a reset back while matching is running, naming the matching', () => {
    const candidate = reset(Status.PENDING);
    const running = matching(Status.RUNNING);
    expect(excludeMatchingDuringReset(candidate, [candidate, running])).toEqual({ on: running.id, reason: WaitingReason.MATCHING });
  });

  it('should not deadlock when a reset and matching are both queued', () => {
    const queuedReset = reset(Status.PENDING);
    const queuedMatching = matching(Status.PENDING);
    const all = [queuedReset, queuedMatching];

    expect(excludeMatchingDuringReset(queuedReset, all)).toBeUndefined();
    expect(excludeMatchingDuringReset(queuedMatching, all)).toMatchObject({ reason: WaitingReason.REDECODE });
  });

  it('should ignore activities that neither reset nor match', () => {
    const candidate = activity({ id: makeActivityId(Kind.TX_SYNC, 'eth'), kind: Kind.TX_SYNC, status: Status.PENDING });
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.RUNNING)])).toBeUndefined();
  });

  it('should not mistake other history-events work for matching, the kind alone being too coarse', () => {
    const candidate = activity({
      id: makeActivityId(Kind.HISTORY_EVENTS, ActivityPart.UNDECODED),
      kind: Kind.HISTORY_EVENTS,
      status: Status.PENDING,
    });
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.RUNNING)])).toBeUndefined();
  });
});

describe('firstRuleHold', () => {
  const hold = { reason: WaitingReason.HISTORY_SYNC };
  const other = { reason: WaitingReason.REDECODE };
  const candidate = balances();
  const admits: EligibilityRule = () => undefined;
  const holds: EligibilityRule = () => hold;
  const holdsOther: EligibilityRule = () => other;

  it('should report the hold of the first rule that holds, in rule order', () => {
    expect(firstRuleHold([admits, holds, holdsOther], candidate, [candidate])).toBe(hold);
  });

  it('should report nothing when every rule lets the candidate start', () => {
    expect(firstRuleHold([admits, admits], candidate, [candidate])).toBeUndefined();
  });
});
