import type {
  HistoricalBalanceFilters,
  HistoricalBalanceSeriesPayload,
  HistoricalBalanceSeriesResponse,
  HistoricalBalancesResponse,
} from '@/modules/history/balances/types';
import { bigNumberify } from '@rotki/common';
import { flushPromises } from '@vue/test-utils';
import { get, set } from '@vueuse/shared';
import dayjs from 'dayjs';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope, nextTick, type Ref, ref } from 'vue';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { AccountHistoryRange } from './account-history-selection';
import { useAccountBalanceSeries } from './use-account-balance-series';

const { fetchBalanceSeries, fetchHistoricalBalances, syncCompleted } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    fetchBalanceSeries: vi.fn<(payload: HistoricalBalanceSeriesPayload) => Promise<HistoricalBalanceSeriesResponse>>(),
    fetchHistoricalBalances: vi.fn<(timestamp: number, filters?: HistoricalBalanceFilters) => Promise<HistoricalBalancesResponse>>(),
    syncCompleted: ref<number>(0),
  };
});

vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: (): Record<string, unknown> => ({ fetchBalanceSeries, fetchHistoricalBalances }),
}));
vi.mock('@/modules/shell/sync-progress/use-sync-completed', () => ({
  useSyncCompleted: (): { syncCompleted: Ref<number> } => ({ syncCompleted }),
}));

const NOW = dayjs('2026-11-13T00:00:00Z').unix();
const MONTH_AGO = dayjs('2026-10-13T00:00:00Z').unix();

function seriesResponse(processingRequired = false): HistoricalBalanceSeriesResponse {
  return {
    entries: [{
      asset: 'ETH',
      location: 'ethereum',
      locationLabel: '0xA',
      protocol: null,
      times: [MONTH_AGO + 10],
      values: [bigNumberify('3')],
    }],
    processingRequired,
  };
}

let scope: EffectScope;

interface Selection {
  account: Ref<string | undefined>;
  asset: Ref<string | undefined>;
  range: Ref<AccountHistoryRange>;
}

function create(initial: { account?: string; asset?: string; range?: AccountHistoryRange } = {}): ReturnType<typeof useAccountBalanceSeries> & Selection {
  const selection: Selection = {
    account: ref<string | undefined>(initial.account ?? '0xA'),
    asset: ref<string | undefined>(initial.asset ?? 'ETH'),
    range: ref<AccountHistoryRange>(initial.range ?? AccountHistoryRange.ALL),
  };
  const state = scope.run(() => useAccountBalanceSeries(selection));
  assert(state);
  return { ...state, ...selection };
}

describe('useAccountBalanceSeries', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(NOW * 1000);
    setActivePinia(createPinia());
    scope = effectScope();
    set(syncCompleted, 0);
    fetchBalanceSeries.mockReset().mockResolvedValue(seriesResponse());
    fetchHistoricalBalances.mockReset().mockResolvedValue({
      entries: [{ amount: bigNumberify('1'), asset: 'ETH', location: 'ethereum', locationLabel: '0xA', protocol: null }],
      processingRequired: false,
    });
  });

  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
  });

  it('should load all time without asking for an opening balance', async () => {
    const { buckets, loadedRange } = create();
    await flushPromises();

    expect(fetchBalanceSeries).toHaveBeenCalledExactlyOnceWith({ asset: 'ETH', fromTimestamp: 0, locationLabel: '0xA', toTimestamp: NOW });
    expect(fetchHistoricalBalances).not.toHaveBeenCalled();
    expect(get(loadedRange)).toEqual({ from: 0, to: NOW });
    expect(get(buckets).map(({ points }) => points.map(({ time, value }) => [time, value.toString()])))
      .toEqual([[[MONTH_AGO + 10, '3'], [NOW, '3']]]);
  });

  it('should start a bounded range from the balance held just before it', async () => {
    const { buckets } = create({ range: AccountHistoryRange.MONTH });
    await flushPromises();

    expect(fetchHistoricalBalances).toHaveBeenCalledExactlyOnceWith(MONTH_AGO - 1, { asset: 'ETH', locationLabel: '0xA' });
    expect(get(buckets)[0]?.points[0]).toEqual({ time: MONTH_AGO, value: bigNumberify('1') });
  });

  it('should report pending processing from either request', async () => {
    fetchBalanceSeries.mockResolvedValue(seriesResponse(true));
    const { processingRequired } = create({ range: AccountHistoryRange.MONTH });
    await flushPromises();

    expect(get(processingRequired)).toBe(true);
  });

  it('should load nothing until both an account and an asset are picked', async () => {
    const { asset, buckets } = create({ asset: '' });
    await flushPromises();

    expect(fetchBalanceSeries).not.toHaveBeenCalled();
    expect(get(buckets)).toEqual([]);

    set(asset, 'ETH');
    await flushPromises();

    expect(fetchBalanceSeries).toHaveBeenCalledOnce();
  });

  it('should forget the loaded range once the asset is unset', async () => {
    const { asset, loadedRange } = create();
    await flushPromises();
    expect(get(loadedRange)).toBeDefined();

    set(asset, undefined);
    await flushPromises();

    expect(get(loadedRange)).toBeUndefined();
  });

  it('should clear the shown series when another asset is picked', async () => {
    const { asset, buckets } = create();
    await flushPromises();
    fetchBalanceSeries.mockReturnValue(new Promise(() => {}));

    set(asset, 'DAI');
    await nextTick();

    expect(get(buckets)).toEqual([]);
  });

  it('should keep the shown series while another range loads', async () => {
    const { buckets, range } = create();
    await flushPromises();
    fetchBalanceSeries.mockReturnValue(new Promise(() => {}));

    set(range, AccountHistoryRange.MONTH);
    await nextTick();

    expect(get(buckets)).toHaveLength(1);
  });

  it('should drop a load that finishes after a newer one started', async () => {
    let resolveFirst!: (value: HistoricalBalanceSeriesResponse) => void;
    fetchBalanceSeries.mockReturnValueOnce(new Promise((resolve) => {
      resolveFirst = resolve;
    }));
    const { asset, buckets } = create();
    fetchBalanceSeries.mockResolvedValueOnce({ entries: [], processingRequired: false });

    set(asset, 'DAI');
    await flushPromises();
    resolveFirst(seriesResponse());
    await flushPromises();

    expect(get(buckets)).toEqual([]);
  });

  it('should show the reason a load failed and nothing else', async () => {
    fetchBalanceSeries.mockRejectedValue(new Error('backend down'));
    const { buckets, error } = create();
    await flushPromises();

    expect(get(error)).toBe('backend down');
    expect(get(buckets)).toEqual([]);
  });

  it('should reload after a history sync and after processing finishes', async () => {
    create();
    await flushPromises();

    set(syncCompleted, 1);
    await flushPromises();
    useHistoricalBalanceProcessingStore().notifyHistoricalBalanceProcessingCompleted();
    await flushPromises();

    expect(fetchBalanceSeries).toHaveBeenCalledTimes(3);
  });

  it('should not reload or clear when the selection re-reads equal values', async () => {
    const query = ref<{ account: string; asset: string; location?: string }>({ account: '0xA', asset: 'ETH' });
    const state = scope.run(() => useAccountBalanceSeries({
      account: () => get(query).account,
      asset: () => get(query).asset,
      range: AccountHistoryRange.ALL,
    }));
    assert(state);
    await flushPromises();
    expect(fetchBalanceSeries).toHaveBeenCalledOnce();

    set(query, { account: '0xA', asset: 'ETH', location: 'ethereum' });
    await nextTick();
    await flushPromises();

    expect(fetchBalanceSeries).toHaveBeenCalledOnce();
    expect(get(state.buckets)).toHaveLength(1);
  });
});
