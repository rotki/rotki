import type { EffectScope, Ref } from 'vue';
import { bigNumberify } from '@rotki/common';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { CostBasisDirection, type CostBasisEntry, type EventsCostBasisResponse } from '@/modules/history/cost-basis/types';
import { useCostBasisOverlay } from '@/modules/history/cost-basis/use-cost-basis-overlay';

const { fetchCostBasis } = vi.hoisted(() => ({
  fetchCostBasis: vi.fn<(ids: number[]) => Promise<EventsCostBasisResponse>>(),
}));

vi.mock('@/modules/history/cost-basis/use-cost-basis-api', () => ({
  useCostBasisApi: (): { fetchEventsCostBasis: typeof fetchCostBasis } => ({ fetchEventsCostBasis: fetchCostBasis }),
}));

const entry: CostBasisEntry = {
  asset: 'ETH',
  basisPerUnit: bigNumberify('10'),
  basisSource: 'price_oracle',
  direction: CostBasisDirection.RECEIVE,
  location: 'ethereum',
  locationLabel: '0xA',
  lotIds: ['1'],
  method: 'fifo',
  protocol: null,
};

function response(ids: number[], stale: number[] = []): EventsCostBasisResponse {
  return { entries: Object.fromEntries(ids.map(id => [String(id), [entry]])), method: 'fifo', stale };
}

const scopes: EffectScope[] = [];

function create(ids: number[], enabled = true): {
  overlay: ReturnType<typeof useCostBasisOverlay>;
  eventIdentifiers: Ref<number[]>;
  enabled: Ref<boolean>;
} {
  const eventIdentifiers = ref<number[]>(ids);
  const enabledRef = ref<boolean>(enabled);
  const scope = effectScope();
  scopes.push(scope);
  const overlay = scope.run(() => useCostBasisOverlay({ enabled: enabledRef, eventIdentifiers }));
  assert(overlay);
  return { enabled: enabledRef, eventIdentifiers, overlay };
}

describe('useCostBasisOverlay', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    fetchCostBasis.mockReset().mockImplementation(async ids => response(ids));
  });

  afterEach(() => {
    scopes.splice(0).forEach(scope => scope.stop());
    vi.useRealTimers();
  });

  it('should fetch page and rendered events once each and keep their entries', async () => {
    const { overlay } = create([1, 1]);
    overlay.registerEvent(2);
    expect(overlay.statusFor(1)).toBe('loading');
    await vi.advanceTimersByTimeAsync(60);

    expect(fetchCostBasis).toHaveBeenCalledExactlyOnceWith([1, 2]);
    expect(overlay.statusFor(1)).toBe('ready');
    expect(overlay.entriesFor(2)).toEqual([entry]);
  });

  it('should keep an event the response has nothing for as empty and not fetch it again', async () => {
    fetchCostBasis.mockImplementation(async () => response([1]));
    const { eventIdentifiers, overlay } = create([1, 2]);
    await vi.advanceTimersByTimeAsync(60);
    expect(overlay.statusFor(2)).toBe('empty');
    expect(overlay.entriesFor(2)).toEqual([]);

    set(eventIdentifiers, [1, 2, 3]);
    await vi.advanceTimersByTimeAsync(60);
    expect(fetchCostBasis).toHaveBeenLastCalledWith([3]);
  });

  it('should show a failed batch as an error and fetch it again on the next change', async () => {
    fetchCostBasis.mockRejectedValueOnce(new Error('boom'));
    const { eventIdentifiers, overlay } = create([1]);
    await vi.advanceTimersByTimeAsync(60);
    expect(overlay.statusFor(1)).toBe('error');

    set(eventIdentifiers, [1, 2]);
    await vi.advanceTimersByTimeAsync(60);
    expect(fetchCostBasis).toHaveBeenLastCalledWith([1, 2]);
    expect(overlay.statusFor(1)).toBe('ready');
  });

  it('should respect the endpoint limit of 500 events per request', async () => {
    create(Array.from({ length: 501 }, (_, index) => index + 1));
    await vi.advanceTimersByTimeAsync(60);
    expect(fetchCostBasis.mock.calls.map(([ids]) => ids.length)).toEqual([500, 1]);
  });

  it('should fetch nothing while disabled and drop what it holds when turned off', async () => {
    const { enabled, overlay } = create([1], false);
    await vi.advanceTimersByTimeAsync(60);
    expect(fetchCostBasis).not.toHaveBeenCalled();

    set(enabled, true);
    await vi.advanceTimersByTimeAsync(60);
    expect(overlay.statusFor(1)).toBe('ready');

    set(enabled, false);
    expect(overlay.entriesFor(1)).toEqual([]);
  });

  it('should mark only stale events as processing, hide their entries, and fetch everything again on refresh', async () => {
    fetchCostBasis.mockImplementation(async () => response([1, 2], [2]));
    const { overlay } = create([1, 2, 3]);
    await vi.advanceTimersByTimeAsync(60);
    expect(overlay.statusFor(1)).toBe('ready');
    expect(overlay.entriesFor(1)).toEqual([entry]);
    expect(overlay.statusFor(2)).toBe('processing');
    expect(overlay.entriesFor(2)).toEqual([]);
    expect(overlay.statusFor(3)).toBe('empty');

    fetchCostBasis.mockImplementation(async () => response([1, 2]));
    await overlay.refresh();
    expect(fetchCostBasis).toHaveBeenLastCalledWith([1, 2, 3]);
    expect(fetchCostBasis).toHaveBeenCalledTimes(2);
    expect(overlay.statusFor(2)).toBe('ready');
    expect(overlay.entriesFor(2)).toEqual([entry]);
  });
});
