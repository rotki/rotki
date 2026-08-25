import type { VueWrapper } from '@vue/test-utils';
import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComputedRef, ref, type Ref } from 'vue';
import { isBinance, useExchangeBalancesPage } from './use-exchange-balances-page';

const {
  connected,
  exchangeBalances,
  pushMock,
  refreshBalance,
  refreshExchangeBalance,
  refreshExchangeSavings,
  routeRef,
} = vi.hoisted(() => {
  const connected: { current: { location: string }[] } = { current: [] };
  const exchangeBalances: { current: Record<string, AssetBalanceWithPrice[]> } = { current: {} };
  const routeRef: { current?: Ref<{ query: Record<string, string> }> } = {};

  return {
    connected,
    exchangeBalances,
    pushMock: vi.fn(async (): Promise<void> => {}),
    refreshBalance: vi.fn(async (): Promise<void> => {}),
    refreshExchangeBalance: vi.fn(async (): Promise<void> => {}),
    refreshExchangeSavings: vi.fn(async (): Promise<void> => {}),
    routeRef,
  };
});

vi.mock('vue-router', async () => {
  const { ref: refFn } = await import('vue');
  return {
    useRoute: (): Ref<{ query: Record<string, string> }> => {
      routeRef.current ??= refFn({ query: {} });
      return routeRef.current;
    },
    useRouter: (): { push: typeof pushMock } => ({ push: pushMock }),
  };
});

vi.mock('@/modules/balances/use-aggregated-balances', () => ({
  useAggregatedBalances: (): { getExchangeBalances: (id: string) => AssetBalanceWithPrice[] } => ({
    getExchangeBalances: (id: string): AssetBalanceWithPrice[] => exchangeBalances.current[id] ?? [],
  }),
}));

vi.mock('@/modules/balances/exchanges/use-binance-savings', () => ({
  useBinanceSavings: (): { refreshExchangeSavings: typeof refreshExchangeSavings } => ({ refreshExchangeSavings }),
}));

vi.mock('@/modules/balances/exchanges/use-connected-exchanges-store', async () => {
  const { computed: computedFn } = await import('vue');
  return {
    useConnectedExchangesStore: (): { connectedExchanges: ComputedRef<{ location: string }[]> } => ({
      connectedExchanges: computedFn(() => connected.current),
    }),
  };
});

vi.mock('@/modules/balances/use-balance-refresh', () => ({
  useBalanceRefresh: (): { refreshBalance: typeof refreshBalance; refreshExchangeBalance: typeof refreshExchangeBalance } => ({
    refreshBalance,
    refreshExchangeBalance,
  }),
}));

vi.mock('@/modules/task-center/use-task-center', async () => {
  const { computed: computedFn } = await import('vue');
  return {
    useTaskCenter: (): { useIsActive: () => ComputedRef<boolean> } => ({
      useIsActive: (): ComputedRef<boolean> => computedFn(() => false),
    }),
  };
});

vi.mock('pinia', async importOriginal => ({
  ...(await importOriginal<typeof import('pinia')>()),
  storeToRefs: (store: Record<string, unknown>): Record<string, unknown> => store,
}));

function balance(asset: string, value: number): AssetBalanceWithPrice {
  return {
    amount: bigNumberify(value),
    asset,
    price: bigNumberify(1),
    value: bigNumberify(value),
  };
}

describe('pages/balances/exchange/isBinance', () => {
  it('should recognise both binance exchanges', () => {
    expect(isBinance('binance')).toBe(true);
    expect(isBinance('binanceus')).toBe(true);
  });

  it('should reject anything else, including nothing at all', () => {
    expect(isBinance('kraken')).toBe(false);
    expect(isBinance('')).toBe(false);
    expect(isBinance(undefined)).toBe(false);
  });
});

describe('pages/balances/exchange/useExchangeBalancesPage', () => {
  // Each harness watches the shared route ref, so a leftover one would answer a later test.
  const mounted: VueWrapper[] = [];

  function setup(exchange?: string): ReturnType<typeof useExchangeBalancesPage> {
    const { result, wrapper } = withSetup(() => useExchangeBalancesPage(() => exchange));
    mounted.push(wrapper);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    connected.current = [];
    exchangeBalances.current = {};
    routeRef.current = ref({ query: {} });
  });

  afterEach(() => {
    while (mounted.length > 0)
      mounted.pop()?.unmount();
  });

  it('should refresh the savings balances on mount', async () => {
    setup();
    await flushPromises();

    expect(refreshExchangeSavings).toHaveBeenCalledTimes(1);
  });

  describe('the connected exchanges', () => {
    it('should list each exchange once, however many keys it has', async () => {
      connected.current = [{ location: 'kraken' }, { location: 'binance' }, { location: 'kraken' }];

      const { usedExchanges } = setup();
      await flushPromises();

      expect(get(usedExchanges)).toEqual(['kraken', 'binance']);
    });

    it('should sort them by balance, largest first', async () => {
      connected.current = [{ location: 'kraken' }, { location: 'binance' }, { location: 'coinbase' }];
      exchangeBalances.current = {
        binance: [balance('BTC', 500)],
        coinbase: [balance('SOL', 50)],
        kraken: [balance('ETH', 100)],
      };

      const { sortedExchanges } = setup();
      await flushPromises();

      expect(get(sortedExchanges)).toEqual(['binance', 'kraken', 'coinbase']);
    });

    it('should not reorder the unsorted list when the sorted one is read', async () => {
      // The mobile picker binds `usedExchanges` and the desktop tabs bind `sortedExchanges`.
      // Sorting in place would silently reorder the picker as soon as the tabs render.
      connected.current = [{ location: 'kraken' }, { location: 'binance' }];
      exchangeBalances.current = { binance: [balance('BTC', 500)], kraken: [balance('ETH', 100)] };

      const { sortedExchanges, usedExchanges } = setup();
      await flushPromises();

      expect(get(sortedExchanges)).toEqual(['binance', 'kraken']);
      expect(get(usedExchanges)).toEqual(['kraken', 'binance']);
    });

    it('should total every asset an exchange holds', async () => {
      exchangeBalances.current = { kraken: [balance('ETH', 100), balance('BTC', 25)] };

      const { exchangeBalance } = setup();
      await flushPromises();

      expect(exchangeBalance('kraken').toNumber()).toBe(125);
    });

    it('should total an exchange with no balances as zero', async () => {
      const { exchangeBalance } = setup();
      await flushPromises();

      expect(exchangeBalance('kraken').toNumber()).toBe(0);
    });
  });

  describe('with no exchange in the route', () => {
    it('should expose no balances, so the page shows its hint', async () => {
      exchangeBalances.current = { kraken: [balance('ETH', 100)] };

      const { balances } = setup();
      await flushPromises();

      expect(get(balances)).toEqual([]);
    });

    it('should start with no tab highlighted', async () => {
      const { modelSelectedTab } = setup();
      await flushPromises();

      expect(get(modelSelectedTab)).toBeUndefined();
    });
  });

  describe('with an exchange in the route', () => {
    it('should expose that exchange balances', async () => {
      exchangeBalances.current = { kraken: [balance('ETH', 100)] };

      const { balances } = setup('kraken');
      await flushPromises();

      expect(get(balances)).toHaveLength(1);
      expect(get(balances)[0].asset).toBe('ETH');
    });

    it('should highlight its tab', async () => {
      const { modelSelectedTab } = setup('kraken');
      await flushPromises();

      expect(get(modelSelectedTab)).toBe('kraken');
    });
  });

  describe('the location query the mobile picker reads', () => {
    it('should be picked up on mount', async () => {
      routeRef.current = ref({ query: { location: 'kraken' } });

      const { modelSelectedExchange } = setup();
      await flushPromises();

      expect(get(modelSelectedExchange)).toBe('kraken');
    });

    it('should follow a later route change', async () => {
      const { modelSelectedExchange } = setup();
      await flushPromises();

      set(routeRef.current!, { query: { location: 'binance' } });
      await flushPromises();

      expect(get(modelSelectedExchange)).toBe('binance');
    });

    it('should open the details for whatever the picker holds', async () => {
      routeRef.current = ref({ query: { location: 'kraken' } });

      const { openExchangeDetails } = setup();
      await flushPromises();
      openExchangeDetails();

      expect(pushMock).toHaveBeenCalledWith({
        name: '/balances/exchange/[[exchange]]',
        params: { exchange: 'kraken' },
      });
    });
  });

  describe('refreshing', () => {
    it('should refresh every exchange and the savings together', async () => {
      const { refreshExchangeBalances } = setup();
      await flushPromises();
      refreshExchangeSavings.mockClear();

      await refreshExchangeBalances();

      expect(refreshBalance).toHaveBeenCalledWith('exchange');
      expect(refreshExchangeSavings).toHaveBeenCalledWith(true);
    });

    it('should refresh the savings alongside a binance refresh', async () => {
      const { refreshSelectedExchangeBalances } = setup();
      await flushPromises();
      refreshExchangeSavings.mockClear();

      await refreshSelectedExchangeBalances('binance');

      expect(refreshExchangeBalance).toHaveBeenCalledWith('binance');
      expect(refreshExchangeSavings).toHaveBeenCalledWith(true);
    });

    it('should not touch the savings for any other exchange', async () => {
      const { refreshSelectedExchangeBalances } = setup();
      await flushPromises();
      refreshExchangeSavings.mockClear();

      await refreshSelectedExchangeBalances('kraken');

      expect(refreshExchangeBalance).toHaveBeenCalledWith('kraken');
      expect(refreshExchangeSavings).not.toHaveBeenCalled();
    });
  });

  it('should send the user to the exchange setup with the add dialog open', async () => {
    const { navigateToExchangeSetup } = setup();
    await flushPromises();

    navigateToExchangeSetup();

    expect(pushMock).toHaveBeenCalledWith({ path: '/api-keys/exchanges', query: { add: 'true' } });
  });
});
