import type { Ref } from 'vue';
import { withSetup } from '@test/utils/with-setup';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LIQUITY_PRICED_ASSETS } from './liquity-assets';
import { useLiquityPage } from './use-liquity-page';

const {
  currencySymbol,
  fetchPools,
  fetchPrices,
  fetchStaking,
  fetchStatistics,
  moduleEnabled,
  resetProtocolStatsPriceQueryStatus,
} = vi.hoisted(() => {
  const currencySymbol: { current?: Ref<string> } = {};
  const moduleEnabled: { current?: Ref<boolean> } = {};

  return {
    currencySymbol,
    fetchPools: vi.fn(async (): Promise<void> => {}),
    fetchPrices: vi.fn(async (): Promise<void> => {}),
    fetchStaking: vi.fn(async (): Promise<void> => {}),
    fetchStatistics: vi.fn(async (): Promise<void> => {}),
    moduleEnabled,
    resetProtocolStatsPriceQueryStatus: vi.fn(),
  };
});

function required<T>(slot: { current?: T }, name: string): T {
  if (slot.current === undefined)
    throw new Error(`${name} was not set up`);

  return slot.current;
}

vi.mock('@/modules/session/use-module-enabled', async () => {
  const actual = await vi.importActual<typeof import('@/modules/session/use-module-enabled')>(
    '@/modules/session/use-module-enabled',
  );
  return {
    ...actual,
    useModuleEnabled: (): { enabled: Ref<boolean> } => ({ enabled: required(moduleEnabled, 'moduleEnabled') }),
  };
});

vi.mock('@/modules/staking/liquity/use-liquity-data-fetching', () => ({
  useLiquityDataFetching: (): Record<string, unknown> => ({ fetchPools, fetchStaking, fetchStatistics }),
}));

vi.mock('@/modules/assets/prices/use-historic-cache-price-store', () => ({
  useHistoricCachePriceStore: (): Record<string, unknown> => ({ resetProtocolStatsPriceQueryStatus }),
}));

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: (): Record<string, unknown> => ({ fetchPrices }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<string> => required(currencySymbol, 'currencySymbol'),
}));

vi.mock('@/modules/premium/use-premium', async () => {
  const { shallowRef } = await import('vue');
  return { usePremium: (): Ref<boolean> => shallowRef(true) };
});

describe('modules/staking/liquity/useLiquityPage', () => {
  function setup(): ReturnType<typeof useLiquityPage> {
    return withSetup(() => useLiquityPage()).result;
  }

  beforeEach(async () => {
    vi.clearAllMocks();
    const { shallowRef } = await import('vue');
    currencySymbol.current = shallowRef('EUR');
    moduleEnabled.current = shallowRef(false);
  });

  it('should not fetch while the module is off', async () => {
    setup();
    await flushPromises();

    expect(fetchStaking).not.toHaveBeenCalled();
    expect(fetchPools).not.toHaveBeenCalled();
    expect(fetchStatistics).not.toHaveBeenCalled();
  });

  it('should fetch immediately when the module is already on', async () => {
    set(required(moduleEnabled, 'moduleEnabled'), true);

    setup();
    await flushPromises();

    expect(fetchStaking).toHaveBeenCalledTimes(1);
  });

  it('should fetch as soon as the module is switched on', async () => {
    setup();
    await flushPromises();

    set(required(moduleEnabled, 'moduleEnabled'), true);
    await flushPromises();

    expect(fetchStaking).toHaveBeenCalledWith(false);
    expect(fetchPools).toHaveBeenCalledWith(false);
    expect(fetchStatistics).toHaveBeenCalledWith(false);
  });

  it('should clear the previous price progress before fetching', async () => {
    set(required(moduleEnabled, 'moduleEnabled'), true);

    setup();
    await flushPromises();

    expect(resetProtocolStatsPriceQueryStatus).toHaveBeenCalledWith('liquity');
    expect(resetProtocolStatsPriceQueryStatus.mock.invocationCallOrder[0])
      .toBeLessThan(fetchStaking.mock.invocationCallOrder[0]);
  });

  it('should pre-fetch a price for every liquity asset', async () => {
    set(required(moduleEnabled, 'moduleEnabled'), true);

    setup();
    await flushPromises();

    expect(fetchPrices).toHaveBeenCalledWith({
      ignoreCache: false,
      selectedAssets: LIQUITY_PRICED_ASSETS,
    });
  });

  describe('when the profit currency changes', () => {
    it('should refetch, ignoring the cache, because every value is denominated in it', async () => {
      set(required(moduleEnabled, 'moduleEnabled'), true);
      setup();
      await flushPromises();
      vi.clearAllMocks();

      set(required(currencySymbol, 'currencySymbol'), 'USD');
      await flushPromises();

      expect(fetchStaking).toHaveBeenCalledWith(true);
      expect(fetchPrices).toHaveBeenCalledWith({ ignoreCache: true, selectedAssets: LIQUITY_PRICED_ASSETS });
    });

    it('should not refetch while the module is off', async () => {
      setup();
      await flushPromises();

      set(required(currencySymbol, 'currencySymbol'), 'USD');
      await flushPromises();

      expect(fetchStaking).not.toHaveBeenCalled();
    });
  });

  it('should refresh on demand, ignoring the cache', async () => {
    set(required(moduleEnabled, 'moduleEnabled'), true);
    const { fetch } = setup();
    await flushPromises();
    vi.clearAllMocks();

    await fetch(true);

    expect(fetchStaking).toHaveBeenCalledWith(true);
  });

  it('should expose the module state and premium status the page branches on', async () => {
    const { moduleEnabled: enabled, premium } = setup();
    await flushPromises();

    expect(get(enabled)).toBe(false);
    expect(get(premium)).toBe(true);
  });
});
