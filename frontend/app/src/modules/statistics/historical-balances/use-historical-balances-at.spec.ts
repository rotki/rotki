import type { HistoricalBalancesResponse } from '@/modules/history/balances/types';
import { bigNumberify } from '@rotki/common';
import { flushPromises } from '@vue/test-utils';
import { get, set } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope, type Ref, ref } from 'vue';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useHistoricalBalancesAt } from './use-historical-balances-at';

const { fetchHistoricalBalances, syncCompleted } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    fetchHistoricalBalances: vi.fn<(timestamp: number) => Promise<HistoricalBalancesResponse>>(),
    syncCompleted: ref<number>(0),
  };
});

vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: (): { fetchHistoricalBalances: typeof fetchHistoricalBalances } => ({ fetchHistoricalBalances }),
}));
vi.mock('@/modules/shell/sync-progress/use-sync-completed', () => ({
  useSyncCompleted: (): { syncCompleted: Ref<number> } => ({ syncCompleted }),
}));

function response(asset: string, processingRequired = false): HistoricalBalancesResponse {
  return {
    entries: [{ amount: bigNumberify('1'), asset, location: 'ethereum', locationLabel: '0xA', protocol: null }],
    processingRequired,
  };
}

function deferred(): { promise: Promise<HistoricalBalancesResponse>; resolve: (value: HistoricalBalancesResponse) => void } {
  let resolve!: (value: HistoricalBalancesResponse) => void;
  const promise = new Promise<HistoricalBalancesResponse>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

let scope: EffectScope;

function create(timestamp: Ref<number>): ReturnType<typeof useHistoricalBalancesAt> {
  const state = scope.run(() => useHistoricalBalancesAt(timestamp));
  assert(state);
  return state;
}

describe('useHistoricalBalancesAt', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    scope = effectScope();
    set(syncCompleted, 0);
    fetchHistoricalBalances.mockReset().mockResolvedValue(response('ETH'));
  });

  afterEach(() => scope.stop());

  it('should load the balances at the timestamp, grouped by asset', async () => {
    const { groups, loading, processingRequired } = create(ref<number>(100));

    expect(get(loading)).toBe(true);
    await flushPromises();

    expect(fetchHistoricalBalances).toHaveBeenCalledExactlyOnceWith(100);
    expect(get(loading)).toBe(false);
    expect(get(groups).map(({ asset }) => asset)).toEqual(['ETH']);
    expect(get(processingRequired)).toBe(false);
  });

  it('should report that events still need processing', async () => {
    fetchHistoricalBalances.mockResolvedValue(response('ETH', true));
    const { processingRequired } = create(ref<number>(100));
    await flushPromises();

    expect(get(processingRequired)).toBe(true);
  });

  it('should reload when the timestamp changes', async () => {
    const timestamp = ref<number>(100);
    create(timestamp);
    await flushPromises();

    set(timestamp, 200);
    await flushPromises();

    expect(fetchHistoricalBalances).toHaveBeenLastCalledWith(200);
  });

  it('should reload when a history sync settles', async () => {
    create(ref<number>(100));
    await flushPromises();

    set(syncCompleted, 1);
    await flushPromises();

    expect(fetchHistoricalBalances).toHaveBeenCalledTimes(2);
  });

  it('should reload when the backend finishes processing events into balances', async () => {
    create(ref<number>(100));
    await flushPromises();

    useHistoricalBalanceProcessingStore().notifyHistoricalBalanceProcessingCompleted();
    await flushPromises();

    expect(fetchHistoricalBalances).toHaveBeenCalledTimes(2);
  });

  it('should drop a load that a newer one overtook', async () => {
    const slow = deferred();
    fetchHistoricalBalances.mockReturnValueOnce(slow.promise).mockResolvedValueOnce(response('DAI'));
    const timestamp = ref<number>(100);
    const { groups } = create(timestamp);

    set(timestamp, 200);
    await flushPromises();
    slow.resolve(response('ETH'));
    await flushPromises();

    expect(get(groups).map(({ asset }) => asset)).toEqual(['DAI']);
  });

  it('should keep the loaded timestamp on the shown balances until the next date arrives', async () => {
    const next = deferred();
    const timestamp = ref<number>(100);
    const { groups, loadedAt } = create(timestamp);
    await flushPromises();

    fetchHistoricalBalances.mockReturnValueOnce(next.promise);
    set(timestamp, 200);
    await flushPromises();
    expect(get(loadedAt)).toBe(100);
    expect(get(groups).map(({ asset }) => asset)).toEqual(['ETH']);

    next.resolve(response('DAI'));
    await flushPromises();
    expect(get(loadedAt)).toBe(200);
    expect(get(groups).map(({ asset }) => asset)).toEqual(['DAI']);
  });

  it('should show a failure and clear the previous date\'s balances', async () => {
    const timestamp = ref<number>(100);
    const { empty, error, groups } = create(timestamp);
    await flushPromises();

    fetchHistoricalBalances.mockRejectedValueOnce(new Error('backend down'));
    set(timestamp, 200);
    await flushPromises();

    expect(get(error)).toBe('backend down');
    expect(get(groups)).toEqual([]);
    expect(get(empty)).toBe(false);
  });

  it('should call a date with no holdings empty', async () => {
    fetchHistoricalBalances.mockResolvedValue({ entries: [], processingRequired: false });
    const { empty } = create(ref<number>(100));
    await flushPromises();

    expect(get(empty)).toBe(true);
  });
});
