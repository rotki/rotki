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

/** What the table shows for a Binance exchange: its balances or its savings interest history. */
type ExchangeView = 'balances' | 'savings';

interface UseExchangeBalancesPageReturn {
  balances: ComputedRef<AssetBalanceWithPrice[]>;
  exchangeBalance: (exchange: string) => BigNumber;
  isExchangeLoading: ComputedRef<boolean>;
  modelView: Ref<ExchangeView>;
  navigateToExchangeSetup: (location?: string) => void;
  refreshExchangeBalances: () => Promise<void>;
  refreshInView: () => Promise<void>;
  refreshSelectedExchangeBalances: (exchangeLocation: string) => Promise<void>;
  sortedExchanges: ComputedRef<string[]>;
  totalBalance: ComputedRef<BigNumber>;
}

function sum(balances: AssetBalanceWithPrice[]): BigNumber {
  return balances.reduce((total, asset) => total.plus(asset.value), Zero);
}

/**
 * The exchange balances page: every connected exchange together, or the one the route names.
 *
 * @param exchange - the exchange in the route, if any; without one the page shows all of them
 */
export function useExchangeBalancesPage(exchange: MaybeRefOrGetter<string | undefined>): UseExchangeBalancesPageReturn {
  const router = useRouter();

  const { useIsActive } = useTaskCenter();
  const { getExchangeBalances } = useAggregatedBalances();
  const { refreshExchangeSavings } = useBinanceSavings();
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { refreshExchangeBalance, refreshExchangeBalances: refreshConnectedExchangeBalances } = useBalanceRefresh();

  const modelView = shallowRef<ExchangeView>('balances');

  const isExchangeLoading = useIsActive(ActivityKind.EXCHANGE_BALANCES);

  function exchangeBalance(exchange: string): BigNumber {
    return sum(getExchangeBalances(exchange));
  }

  /** One entry per exchange, however many keys it has, largest balance first. */
  const sortedExchanges = computed<string[]>(() =>
    get(connectedExchanges)
      .map(({ location }) => location)
      .filter(uniqueStrings)
      .sort((a, b) => exchangeBalance(b).minus(exchangeBalance(a)).toNumber()),
  );

  const balances = computed<AssetBalanceWithPrice[]>(() => getExchangeBalances(toValue(exchange)));

  const totalBalance = computed<BigNumber>(() => sum(getExchangeBalances()));

  async function refreshExchangeBalances(): Promise<void> {
    await Promise.all([refreshConnectedExchangeBalances(), refreshExchangeSavings(true)]);
  }

  /** Binance also has savings balances, which the generic refresh does not cover. */
  async function refreshSelectedExchangeBalances(exchangeLocation: string): Promise<void> {
    if (isBinance(exchangeLocation))
      await Promise.all([refreshExchangeBalance(exchangeLocation), refreshExchangeSavings(true)]);
    else
      await refreshExchangeBalance(exchangeLocation);
  }

  /** The page's Refresh: the exchange in view, or every exchange when the page shows them all. */
  async function refreshInView(): Promise<void> {
    const current = toValue(exchange);
    if (current)
      await refreshSelectedExchangeBalances(current);
    else
      await refreshExchangeBalances();
  }

  function navigateToExchangeSetup(location?: string): void {
    startPromise(router.push({
      path: '/api-keys/exchanges',
      query: location ? { add: 'true', location } : { add: 'true' },
    }));
  }

  onMounted(() => {
    startPromise(refreshExchangeSavings());
  });

  // A different exchange starts on its balances rather than inheriting the previous one's view.
  watch(() => toValue(exchange), () => {
    set(modelView, 'balances');
  });

  return {
    balances,
    exchangeBalance,
    isExchangeLoading,
    modelView,
    navigateToExchangeSetup,
    refreshExchangeBalances,
    refreshInView,
    refreshSelectedExchangeBalances,
    sortedExchanges,
    totalBalance,
  };
}
