import type { QueuedRequest } from './types';
import { describe, expect, it, vi } from 'vitest';
import { RequestPriority } from './request-priority';
import { findEligibleIndex } from './slot-policy';

let stubId = 0;

/** A complete queued request, so the policy is exercised against the real shape. */
function request(priority: number): QueuedRequest {
  stubId += 1;
  return {
    abortController: new AbortController(),
    dedupeKey: null,
    id: `stub-${stubId}`,
    maxQueueTime: 60_000,
    maxRetries: 0,
    options: {},
    priority,
    queuedAt: 0,
    reject: vi.fn(),
    resolve: vi.fn(),
    retries: 0,
    tags: [],
    url: `/stub-${stubId}`,
  };
}

describe('findEligibleIndex', () => {
  const background = request(RequestPriority.LOW);
  const normal = request(RequestPriority.NORMAL);
  const critical = request(RequestPriority.CRITICAL);

  it('should take the head while background work is under its cap', () => {
    expect(findEligibleIndex([background, normal], [], 2)).toBe(0);
    expect(findEligibleIndex([background, normal], [background], 2)).toBe(0);
  });

  it('should skip past background work once the cap is reached', () => {
    const active = [background, background];

    expect(findEligibleIndex([background, background, critical], active, 2)).toBe(2);
  });

  it('should report nothing eligible when only capped background work waits', () => {
    const active = [background, background];

    expect(findEligibleIndex([background, background], active, 2)).toBe(-1);
  });

  it('should report nothing eligible for an empty queue', () => {
    expect(findEligibleIndex([], [], 2)).toBe(-1);
    expect(findEligibleIndex([], [background, background], 2)).toBe(-1);
  });

  it('should not count foreground work against the background cap', () => {
    const active = [normal, critical, normal, critical, normal];

    expect(findEligibleIndex([background], active, 2)).toBe(0);
  });

  it('should treat BACKGROUND as capped alongside LOW', () => {
    const active = [request(RequestPriority.BACKGROUND), request(RequestPriority.BACKGROUND)];

    expect(findEligibleIndex([request(RequestPriority.BACKGROUND)], active, 2)).toBe(-1);
  });

  it('should let a cap of zero block background work entirely', () => {
    expect(findEligibleIndex([background, normal], [], 0)).toBe(1);
  });
});
