import type { EffectScope, Ref } from 'vue';
import type { HistoricalBalancesAtEventsResponse } from './types';
import { bigNumberify } from '@rotki/common';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountingOverlay } from './use-accounting-overlay';

const { fetchSnapshots } = vi.hoisted(() => ({
  fetchSnapshots: vi.fn<(ids: number[]) => Promise<HistoricalBalancesAtEventsResponse>>(),
}));

vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: (): { fetchHistoricalBalancesAtEvents: typeof fetchSnapshots } => ({ fetchHistoricalBalancesAtEvents: fetchSnapshots }),
}));

function response(ids: number[], balance = '5'): HistoricalBalancesAtEventsResponse {
  return { entries: Object.fromEntries(ids.map(id => [String(id), {
    processingRequired: false,
    buckets: [{ location: 'ethereum', protocol: null, balance: bigNumberify(balance) }],
  }])) };
}

const scopes: EffectScope[] = [];

function create(ids: number[], enabled = true): {
  overlay: ReturnType<typeof useAccountingOverlay>;
  eventIdentifiers: Ref<number[]>;
  enabled: Ref<boolean>;
} {
  const eventIdentifiers = ref<number[]>(ids);
  const enabledRef = ref<boolean>(enabled);
  const scope = effectScope();
  scopes.push(scope);
  const overlay = scope.run(() => useAccountingOverlay({ enabled: enabledRef, eventIdentifiers }));
  assert(overlay);
  return { overlay, eventIdentifiers, enabled: enabledRef };
}

describe('useAccountingOverlay event batches', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    fetchSnapshots.mockReset().mockImplementation(async ids => response(ids));
  });

  afterEach(() => {
    scopes.splice(0).forEach(scope => scope.stop());
    vi.useRealTimers();
  });

  it('should batch page and rendered events, deduplicate IDs and preserve each exact snapshot', async () => {
    fetchSnapshots.mockResolvedValue({ entries: {
      ...response([1], '0').entries,
      2: {
        processingRequired: false,
        buckets: [
          { location: 'base', protocol: null, balance: bigNumberify('0.1234567890123456789') },
          { location: 'ethereum', protocol: 'aave', balance: bigNumberify('2') },
        ],
      },
    } });
    const { overlay } = create([1, 1]);
    overlay.registerEvent(1);
    overlay.registerEvent(2);
    await vi.advanceTimersByTimeAsync(60);

    expect(fetchSnapshots).toHaveBeenCalledExactlyOnceWith([1, 2]);
    expect(overlay.balanceAfter(1)?.toString()).toBe('0');
    expect(overlay.balanceAfter(2)?.toString()).toBe('2.1234567890123456789');
    expect(overlay.bucketsAt(2)).toHaveLength(2);
    expect(overlay.statusFor(1)).toBe('ready');
  });

  it('should fetch only new events when the page changes and release unmounted registrations', async () => {
    const { overlay, eventIdentifiers } = create([1]);
    const unregister = overlay.registerEvent(2);
    await vi.advanceTimersByTimeAsync(60);
    unregister();
    set(eventIdentifiers, [1, 3]);
    await vi.advanceTimersByTimeAsync(60);
    expect(fetchSnapshots).toHaveBeenLastCalledWith([3]);

    await overlay.refresh();
    expect(fetchSnapshots).toHaveBeenLastCalledWith([1, 3]);
  });

  it('should keep a rendered event registered until its final cell unmounts', async () => {
    const { overlay } = create([]);
    const first = overlay.registerEvent(1);
    const second = overlay.registerEvent(1);
    first();
    await vi.advanceTimersByTimeAsync(60);
    expect(fetchSnapshots).toHaveBeenCalledExactlyOnceWith([1]);
    second();
    await overlay.refresh();
    expect(fetchSnapshots).toHaveBeenCalledTimes(1);
  });

  it('should respect the endpoint limit of 500 IDs', async () => {
    create(Array.from({ length: 501 }, (_, index) => index + 1));
    await vi.advanceTimersByTimeAsync(60);
    expect(fetchSnapshots.mock.calls.map(([ids]) => ids.length)).toEqual([500, 1]);
  });

  it('should distinguish empty, incomplete and missing results without displaying incomplete totals', async () => {
    fetchSnapshots.mockResolvedValue({ entries: {
      1: { processingRequired: false, buckets: [] },
      2: { ...response([2]).entries['2'], processingRequired: true },
    } });
    const { overlay } = create([1, 2, 3]);
    await vi.advanceTimersByTimeAsync(60);
    expect(overlay.statusFor(1)).toBe('empty');
    expect(overlay.statusFor(2)).toBe('processing');
    expect(overlay.statusFor(3)).toBe('error');
    expect(overlay.balanceAfter(2)).toBeUndefined();
  });

  it('should mark all events in a failed batch as errors', async () => {
    fetchSnapshots.mockRejectedValue(new Error('unavailable'));
    const { overlay } = create([1, 2]);
    await vi.advanceTimersByTimeAsync(60);
    expect(overlay.statusFor(1)).toBe('error');
    expect(overlay.statusFor(2)).toBe('error');
  });

  it('should discard a late result from before a refresh', async () => {
    let resolvePending: (result: HistoricalBalancesAtEventsResponse) => void = () => {};
    fetchSnapshots.mockReturnValueOnce(new Promise<HistoricalBalancesAtEventsResponse>((resolve) => {
      resolvePending = resolve;
    }));
    const { overlay } = create([1]);
    await vi.advanceTimersByTimeAsync(60);
    fetchSnapshots.mockResolvedValue(response([1], '7'));
    await overlay.refresh();
    resolvePending(response([1], '1'));
    await vi.advanceTimersByTimeAsync(60);
    expect(overlay.balanceAfter(1)?.toString()).toBe('7');
  });

  it('should stay idle while disabled and fetch when enabled', async () => {
    const { overlay, enabled } = create([1], false);
    await vi.advanceTimersByTimeAsync(60);
    expect(fetchSnapshots).not.toHaveBeenCalled();
    expect(get(overlay.state)).toBe('disabled');
    set(enabled, true);
    await vi.advanceTimersByTimeAsync(60);
    expect(fetchSnapshots).toHaveBeenCalledExactlyOnceWith([1]);
  });
});
