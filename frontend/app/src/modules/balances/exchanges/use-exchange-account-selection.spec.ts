import type { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { createTestExchange } from '@test/utils/create-data';
import { withSetup } from '@test/utils/with-setup';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { nextTick, ref, type Ref } from 'vue';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useExchangeAccountSelection } from './use-exchange-account-selection';

type Query = Record<string, string | undefined>;

const { route, router } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  const route = ref<{ query: Query }>({ query: {} });
  return {
    route,
    router: {
      replace: vi.fn(async ({ query }: { query: Query }): Promise<void> => {
        route.value = { query };
      }),
    },
  };
});

vi.mock('vue-router', () => ({
  useRoute: (): Ref<{ query: Query }> => route,
  useRouter: (): { replace: Mock } => router,
}));

const threshold = vi.hoisted((): { value?: string } => ({}));

vi.mock('@/modules/assets/amount-display/use-usd-value-threshold', async () => {
  const { computed } = await import('vue');
  return {
    useValueThreshold: (): ReturnType<typeof useValueThreshold> => computed<string | undefined>(() => threshold.value),
  };
});

const accountBalances = vi.hoisted((): Record<string, Record<string, AssetBalanceWithPrice[]>> => ({}));

vi.mock('@/modules/balances/use-aggregated-balances', () => ({
  useAggregatedBalances: (): { getExchangeAccountBalances: (exchange: string, identifier: string) => AssetBalanceWithPrice[] } => ({
    getExchangeAccountBalances: (exchange: string, identifier: string): AssetBalanceWithPrice[] =>
      accountBalances[exchange]?.[identifier] ?? [],
  }),
}));

function row(asset: string, value: number): AssetBalanceWithPrice {
  return { amount: bigNumberify(1), asset, price: bigNumberify(value), value: bigNumberify(value) };
}

describe('useExchangeAccountSelection', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(route, { query: {} });
    threshold.value = undefined;
    for (const key of Object.keys(accountBalances))
      delete accountBalances[key];

    accountBalances.kraken = {
      'kraken-Bot': [row('SOL', 300)],
      'kraken-Main': [row('BTC', 1000), row('ETH', 500), row('USDT', 0.4)],
    };
    useConnectedExchangesStore().setConnectedExchanges([
      createTestExchange('kraken', 'Bot'),
      createTestExchange('kraken', 'Main'),
      createTestExchange('coinbase', 'Only'),
    ]);
  });

  it('should offer each connection of an exchange largest first, with its total value and share', () => {
    const { result } = withSetup(() => useExchangeAccountSelection('kraken'));

    expect(get(result.accounts).map(({ identifier, name, share, value }) => [identifier, name, value.toNumber(), share])).toEqual([
      ['kraken-Main', 'Main', 1500.4, '83.34'],
      ['kraken-Bot', 'Bot', 300, '16.66'],
    ]);
  });

  it('should offer nothing to pick for an exchange with a single connection', () => {
    const { result } = withSetup(() => useExchangeAccountSelection('coinbase'));

    expect(get(result.accounts)).toEqual([]);
  });

  it('should offer nothing to pick on the all exchanges view', () => {
    const { result } = withSetup(() => useExchangeAccountSelection(undefined));

    expect(get(result.accounts)).toEqual([]);
  });

  it('should tell an account no refresh has loaded from one holding nothing', () => {
    accountBalances.kraken['kraken-Bot'] = [];
    useBalancesStore().exchangeAccountBalances = { kraken: { 'kraken-Bot': {} } };
    const { result } = withSetup(() => useExchangeAccountSelection('kraken'));

    expect(get(result.accounts).map(({ identifier, loaded }) => [identifier, loaded])).toEqual([
      ['kraken-Main', false],
      ['kraken-Bot', true],
    ]);
  });

  it('should carry the reason a connection failed its last refresh', () => {
    useBalancesStore().exchangeFailedAccounts = { kraken: { 'kraken-Bot': 'Invalid key' } };
    const { result } = withSetup(() => useExchangeAccountSelection('kraken'));

    expect(get(result.accounts).map(({ error, identifier }) => [identifier, error])).toEqual([
      ['kraken-Main', undefined],
      ['kraken-Bot', 'Invalid key'],
    ]);
  });

  it('should give no account balances until a connection is picked, then that connection only', async () => {
    const { result } = withSetup(() => useExchangeAccountSelection('kraken'));

    expect(get(result.accountBalances)).toBeUndefined();

    set(result.modelAccount, 'kraken-Bot');
    await nextTick();

    expect(get(result.accountBalances)?.map(({ asset }) => asset)).toEqual(['SOL']);
  });

  describe('in the route query', () => {
    it('should write the pick to the query, keeping the rest of it', () => {
      set(route, { query: { other: 'kept' } });
      const { result } = withSetup(() => useExchangeAccountSelection('kraken'));

      set(result.modelAccount, 'kraken-Bot');

      expect(router.replace).toHaveBeenCalledWith({ query: { account: 'kraken-Bot', other: 'kept' } });
    });

    it('should drop the pick from the query when going back to all accounts', () => {
      set(route, { query: { account: 'kraken-Bot', other: 'kept' } });
      const { result } = withSetup(() => useExchangeAccountSelection('kraken'));

      set(result.modelAccount, undefined);

      expect(router.replace).toHaveBeenCalledWith({ query: { other: 'kept' } });
    });

    it('should restore a pick the query already names', () => {
      set(route, { query: { account: 'kraken-Bot' } });
      const { result } = withSetup(() => useExchangeAccountSelection('kraken'));

      expect(get(result.modelAccount)).toBe('kraken-Bot');
      expect(get(result.accountBalances)?.map(({ asset }) => asset)).toEqual(['SOL']);
    });

    it('should read a pick of another exchange as all accounts', () => {
      set(route, { query: { account: 'kraken-Bot' } });
      const exchange = ref<string>('kraken');
      const { result } = withSetup(() => useExchangeAccountSelection(exchange));

      set(exchange, 'coinbase');

      expect(get(result.modelAccount)).toBeUndefined();
      expect(get(result.accountBalances)).toBeUndefined();
    });

    it('should keep a pick in the query until its connection loads', () => {
      useConnectedExchangesStore().setConnectedExchanges([]);
      set(route, { query: { account: 'kraken-Bot' } });
      const { result } = withSetup(() => useExchangeAccountSelection('kraken'));

      expect(get(result.modelAccount)).toBeUndefined();

      useConnectedExchangesStore().setConnectedExchanges([
        createTestExchange('kraken', 'Bot'),
        createTestExchange('kraken', 'Main'),
      ]);

      expect(get(result.modelAccount)).toBe('kraken-Bot');
      expect(router.replace).not.toHaveBeenCalled();
    });

    it('should fall back to every connection when the picked one is removed', () => {
      set(route, { query: { account: 'kraken-Bot' } });
      const { result } = withSetup(() => useExchangeAccountSelection('kraken'));

      useConnectedExchangesStore().setConnectedExchanges([
        createTestExchange('kraken', 'Main'),
        createTestExchange('kraken', 'Savings'),
      ]);

      expect(get(result.modelAccount)).toBeUndefined();
      expect(get(result.accountBalances)).toBeUndefined();
    });
  });

  describe('with a hide small balances threshold', () => {
    beforeEach(() => {
      threshold.value = '1';
    });

    it('should leave out the picked account assets at or below the threshold', () => {
      set(route, { query: { account: 'kraken-Main' } });
      const { result } = withSetup(() => useExchangeAccountSelection('kraken'));

      expect(get(result.accountBalances)?.map(({ asset }) => asset)).toEqual(['BTC', 'ETH']);
    });

    it('should total each account without the assets the threshold hides', () => {
      const { result } = withSetup(() => useExchangeAccountSelection('kraken'));

      expect(get(result.accounts).find(({ identifier }) => identifier === 'kraken-Main')?.value.toNumber()).toBe(1500);
    });
  });
});
