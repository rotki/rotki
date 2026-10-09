import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComputedRef, ref, type Ref } from 'vue';
import { isBinance, useExchangeBalancesPage } from './use-exchange-balances-page';

const {
  connected,
  exchangeBalances,
  pushMock,
  refreshConnectedExchangeBalances,
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
    refreshConnectedExchangeBalances: vi.fn(async (): Promise<void> => {}),
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
  useAggregatedBalances: (): { getExchangeBalances: (id?: string) => AssetBalanceWithPrice[] } => ({
    // without an exchange, every exchange's rows together, as the real aggregation sums them
    getExchangeBalances: (id?: string): AssetBalanceWithPrice[] => (id
      ? exchangeBalances.current[id] ?? []
      : Object.values(exchangeBalances.current).flat()),
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
  useBalanceRefresh: (): { refreshExchangeBalance: typeof refreshExchangeBalance; refreshExchangeBalances: typeof refreshConnectedExchangeBalances } => ({
    refreshExchangeBalance,
    refreshExchangeBalances: refreshConnectedExchangeBalances,
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
  function setup(exchange?: string): ReturnType<typeof useExchangeBalancesPage> {
    return withSetup(() => useExchangeBalancesPage(() => exchange)).result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    connected.current = [];
    exchangeBalances.current = {};
    routeRef.current = ref({ query: {} });
  });

  it('should refresh the savings balances on mount', async () => {
    setup();
    await flushPromises();

    expect(refreshExchangeSavings).toHaveBeenCalledTimes(1);
  });

  describe('the connected exchanges', () => {
    it('should list each exchange once, however many keys it has', async () => {
      connected.current = [{ location: 'kraken' }, { location: 'binance' }, { location: 'kraken' }];

      const { sortedExchanges } = setup();
      await flushPromises();

      expect(get(sortedExchanges)).toEqual(['kraken', 'binance']);
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
    it('should expose every exchange balances together', async () => {
      exchangeBalances.current = { binance: [balance('BTC', 500)], kraken: [balance('ETH', 100)] };

      const { balances } = setup();
      await flushPromises();

      expect(get(balances).map(({ asset }) => asset)).toEqual(['BTC', 'ETH']);
    });

    it('should refresh every exchange from the page refresh', async () => {
      const { refreshInView } = setup();
      await flushPromises();
      refreshExchangeSavings.mockClear();

      await refreshInView();

      expect(refreshConnectedExchangeBalances).toHaveBeenCalledOnce();
      expect(refreshExchangeBalance).not.toHaveBeenCalled();
    });
  });

  it('should total every exchange, whichever one is in view', async () => {
    exchangeBalances.current = { binance: [balance('BTC', 500)], kraken: [balance('ETH', 100)] };

    const { totalBalance } = setup('kraken');
    await flushPromises();

    expect(get(totalBalance).toNumber()).toBe(600);
  });

  describe('with an exchange in the route', () => {
    it('should expose that exchange balances', async () => {
      exchangeBalances.current = { kraken: [balance('ETH', 100)] };

      const { balances } = setup('kraken');
      await flushPromises();

      expect(get(balances)).toHaveLength(1);
      expect(get(balances)[0].asset).toBe('ETH');
    });

    it('should refresh only that exchange from the page refresh', async () => {
      const { refreshInView } = setup('kraken');
      await flushPromises();

      await refreshInView();

      expect(refreshExchangeBalance).toHaveBeenCalledWith('kraken');
      expect(refreshConnectedExchangeBalances).not.toHaveBeenCalled();
    });

    it('should start on the balances view', async () => {
      const { modelView } = setup('binance');
      await flushPromises();

      expect(get(modelView)).toBe('balances');
    });
  });

  describe('refreshing', () => {
    it('should refresh every exchange and the savings together', async () => {
      const { refreshExchangeBalances } = setup();
      await flushPromises();
      refreshExchangeSavings.mockClear();

      await refreshExchangeBalances();

      expect(refreshConnectedExchangeBalances).toHaveBeenCalledOnce();
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

  it('should open the add dialog on a given exchange', async () => {
    const { navigateToExchangeSetup } = setup();
    await flushPromises();

    navigateToExchangeSetup('kraken');

    expect(pushMock).toHaveBeenCalledWith({ path: '/api-keys/exchanges', query: { add: 'true', location: 'kraken' } });
  });
});
