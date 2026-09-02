import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { type AssetBalanceWithPrice, type BigNumber, Zero } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useBinanceSavings } from '@/modules/balances/exchanges/use-binance-savings';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/** The two exchanges that also hold savings balances, which refresh alongside the main ones. */
const BINANCE_EXCHANGES = ['binance', 'binanceus'];

export function isBinance(exchange?: string): exchange is 'binance' | 'binanceus' {
  return !!exchange && BINANCE_EXCHANGES.includes(exchange);
}

interface UseExchangeBalancesPageReturn {
  balances: ComputedRef<AssetBalanceWithPrice[]>;
  exchangeBalance: (exchange: string) => BigNumber;
  isExchangeLoading: ComputedRef<boolean>;
  modelExchangeDetailTabs: Ref<number>;
  modelSelectedExchange: Ref<string>;
  modelSelectedTab: Ref<string | undefined>;
  navigateToExchangeSetup: () => void;
  openExchangeDetails: () => void;
  refreshExchangeBalances: () => Promise<void>;
  refreshSelectedExchangeBalances: (exchangeLocation: string) => Promise<void>;
  sortedExchanges: ComputedRef<string[]>;
  usedExchanges: ComputedRef<string[]>;
}

export function useExchangeBalancesPage(exchange: MaybeRefOrGetter<string | undefined>): UseExchangeBalancesPageReturn {
  const router = useRouter();
  const route = useRoute();

  const { useIsActive } = useTaskCenter();
  const { getExchangeBalances } = useAggregatedBalances();
  const { refreshExchangeSavings } = useBinanceSavings();
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { refreshBalance, refreshExchangeBalance } = useBalanceRefresh();

  /**
   * Seeded from the route once, and only ever the initially highlighted tab: the tabs are links, so
   * the router is what drives the page from there.
   */
  const modelSelectedTab = shallowRef<string | undefined>(toValue(exchange) ?? undefined);
  const modelSelectedExchange = shallowRef<string>('');
  const modelExchangeDetailTabs = shallowRef<number>(0);

  const isExchangeLoading = useIsActive(ActivityKind.EXCHANGE_BALANCES);

  const usedExchanges = computed<string[]>(() =>
    get(connectedExchanges)
      .map(({ location }) => location)
      .filter(uniqueStrings),
  );

  function exchangeBalance(exchange: string): BigNumber {
    return getExchangeBalances(exchange).reduce(
      (sum, asset: AssetBalanceWithPrice) => sum.plus(asset.value),
      Zero,
    );
  }

  /**
   * The exchanges by balance, largest first, for the desktop tabs.
   *
   * @remarks
   * Sorts a copy. `sort` in place would reorder the array {@link usedExchanges} has cached, so
   * rendering the tabs would silently reorder the mobile picker bound to it.
   */
  const sortedExchanges = computed<string[]>(() =>
    [...get(usedExchanges)].sort((a, b) => exchangeBalance(b).minus(exchangeBalance(a)).toNumber()),
  );

  const balances = computed<AssetBalanceWithPrice[]>(() => {
    const current = toValue(exchange);
    if (!current)
      return [];

    return getExchangeBalances(current);
  });

  async function refreshExchangeBalances(): Promise<void> {
    await Promise.all([refreshBalance('exchange'), refreshExchangeSavings(true)]);
  }

  /** Binance also has savings balances, which the generic refresh does not cover. */
  async function refreshSelectedExchangeBalances(exchangeLocation: string): Promise<void> {
    if (isBinance(exchangeLocation))
      await Promise.all([refreshExchangeBalance(exchangeLocation), refreshExchangeSavings(true)]);
    else
      await refreshExchangeBalance(exchangeLocation);
  }

  function openExchangeDetails(): void {
    startPromise(router.push({
      name: '/balances/exchange/[[exchange]]',
      params: { exchange: get(modelSelectedExchange) },
    }));
  }

  function navigateToExchangeSetup(): void {
    startPromise(router.push({
      path: '/api-keys/exchanges',
      query: { add: 'true' },
    }));
  }

  function setSelectedExchange(): void {
    set(modelSelectedExchange, get(route).query.location);
  }

  onMounted(() => {
    setSelectedExchange();
    startPromise(refreshExchangeSavings());
  });

  watch(route, () => {
    setSelectedExchange();
  });

  // A different exchange starts on its own first tab rather than inheriting the previous one's.
  watch(() => toValue(exchange), () => {
    set(modelExchangeDetailTabs, 0);
  });

  return {
    balances,
    exchangeBalance,
    isExchangeLoading,
    modelExchangeDetailTabs,
    modelSelectedExchange,
    modelSelectedTab,
    navigateToExchangeSetup,
    openExchangeDetails,
    refreshExchangeBalances,
    refreshSelectedExchangeBalances,
    sortedExchanges,
    usedExchanges,
  };
}
