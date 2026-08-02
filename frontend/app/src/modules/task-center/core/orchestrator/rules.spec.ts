import { describe, expect, it } from 'vitest';
import {
  type Activity,
  ActivityPart,
  ActivitySourceType,
  ActivityKind as Kind,
  makeActivityId,
  ActivityStatus as Status,
} from '../types';
import { excludeMatchingDuringReset } from './rules';

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

describe('excludeMatchingDuringReset', () => {
  it('should hold matching back while a reset is running', () => {
    const candidate = matching(Status.PENDING);
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.RUNNING)])).toBe(false);
  });

  it('should hold matching back while a reset is merely queued', () => {
    // Yielding to a queued reset is what stops a stream of matching work starving it.
    const candidate = matching(Status.PENDING);
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.PENDING)])).toBe(false);
  });

  it('should cover bridge matching as well as asset-movement matching', () => {
    const candidate = bridgeMatching(Status.PENDING);
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.RUNNING)])).toBe(false);
  });

  it('should let matching run once the reset has settled', () => {
    const candidate = matching(Status.PENDING);
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.COMPLETE)])).toBe(true);
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.FAILED)])).toBe(true);
  });

  it('should hold a reset back while matching is running', () => {
    const candidate = reset(Status.PENDING);
    expect(excludeMatchingDuringReset(candidate, [candidate, matching(Status.RUNNING)])).toBe(false);
  });

  it('should not deadlock when a reset and matching are both queued', () => {
    // The asymmetry is the point: matching yields to a queued reset, but a reset only yields to
    // matching that is already running. So with both queued the reset starts and the pair resolves,
    // where a symmetric rule would leave each waiting on the other forever.
    const queuedReset = reset(Status.PENDING);
    const queuedMatching = matching(Status.PENDING);
    const all = [queuedReset, queuedMatching];

    expect(excludeMatchingDuringReset(queuedReset, all)).toBe(true);
    expect(excludeMatchingDuringReset(queuedMatching, all)).toBe(false);
  });

  it('should ignore activities that neither reset nor match', () => {
    const candidate = activity({ id: makeActivityId(Kind.TX_SYNC, 'eth'), kind: Kind.TX_SYNC, status: Status.PENDING });
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.RUNNING)])).toBe(true);
  });

  it('should not mistake other history-events work for matching', () => {
    // The kind alone is too coarse — undecoded counts live under it too.
    const candidate = activity({
      id: makeActivityId(Kind.HISTORY_EVENTS, ActivityPart.UNDECODED),
      kind: Kind.HISTORY_EVENTS,
      status: Status.PENDING,
    });
    expect(excludeMatchingDuringReset(candidate, [candidate, reset(Status.RUNNING)])).toBe(true);
  });
});
