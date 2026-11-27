import type { HistoricalBalanceAssetsPayload, HistoricalBalanceAssetsResponse } from '@/modules/history/balances/types';
import { flushPromises } from '@vue/test-utils';
import { get, set } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope, type Ref, ref } from 'vue';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useAccountAssets } from './use-account-assets';

const { fetchHistoricalBalanceAssets, syncCompleted } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    fetchHistoricalBalanceAssets: vi.fn<(payload: HistoricalBalanceAssetsPayload) => Promise<HistoricalBalanceAssetsResponse>>(),
    syncCompleted: ref<number>(0),
  };
});

vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: (): Record<string, unknown> => ({ fetchHistoricalBalanceAssets }),
}));
vi.mock('@/modules/shell/sync-progress/use-sync-completed', () => ({
  useSyncCompleted: (): { syncCompleted: Ref<number> } => ({ syncCompleted }),
}));

let scope: EffectScope;

function create(account: Ref<string | undefined>): ReturnType<typeof useAccountAssets> {
  const state = scope.run(() => useAccountAssets(account));
  assert(state);
  return state;
}

describe('useAccountAssets', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    scope = effectScope();
    fetchHistoricalBalanceAssets.mockReset().mockResolvedValue({ entries: ['ETH', 'DAI'], processingRequired: false });
  });

  afterEach(() => scope.stop());

  it('should list the assets the picked account has held', async () => {
    const { assets, processingRequired } = create(ref<string | undefined>('0xA'));
    await flushPromises();

    expect(fetchHistoricalBalanceAssets).toHaveBeenCalledExactlyOnceWith({ locationLabel: '0xA' });
    expect(get(assets)).toEqual(['ETH', 'DAI']);
    expect(get(processingRequired)).toBe(false);
  });

  it('should report that the list may be short while events are unprocessed', async () => {
    fetchHistoricalBalanceAssets.mockResolvedValue({ entries: [], processingRequired: true });
    const { assets, processingRequired } = create(ref<string | undefined>('0xA'));
    await flushPromises();

    expect(get(assets)).toEqual([]);
    expect(get(processingRequired)).toBe(true);
  });

  it('should list nothing and ask for nothing without an account', async () => {
    const account = ref<string | undefined>('0xA');
    const { assets } = create(account);
    await flushPromises();

    set(account, undefined);
    await flushPromises();

    expect(fetchHistoricalBalanceAssets).toHaveBeenCalledOnce();
    expect(get(assets)).toEqual([]);
  });

  it('should report why the list could not load', async () => {
    fetchHistoricalBalanceAssets.mockRejectedValue(new Error('not found'));
    const { assets, error } = create(ref<string | undefined>('0xA'));
    await flushPromises();

    expect(get(error)).toBe('not found');
    expect(get(assets)).toEqual([]);
  });

  it('should reload once processing finishes, since it can add assets', async () => {
    create(ref<string | undefined>('0xA'));
    await flushPromises();

    useHistoricalBalanceProcessingStore().notifyHistoricalBalanceProcessingCompleted();
    await flushPromises();

    expect(fetchHistoricalBalanceAssets).toHaveBeenCalledTimes(2);
  });
});
