import { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import { ProfitLossModel } from '@rotki/common/lib/defi';
import {
  BalancerBalanceWithOwner,
  BalancerEvent,
  BalancerProfitLoss,
  Pool
} from '@rotki/common/lib/defi/balancer';
import {
  AdexApi,
  AssetsApi,
  BalancerApi,
  BalancesApi,
  CompoundApi,
  DexTradesApi,
  StatisticsApi,
  SushiApi,
  UserSettingsApi,
  UtilsApi
} from '@rotki/common/lib/premium';
import { AdexBalances, AdexHistory } from '@rotki/common/lib/staking/adex';
import {
  LocationData,
  OwnedAssets,
  TimedAssetBalances,
  TimedBalances
} from '@rotki/common/lib/statistics';
import { computed } from '@vue/composition-api';
import { get, toRefs } from '@vueuse/core';
import { truncateAddress } from '@/filters';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval, useIgnoredAssetsStore } from '@/store/assets';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { useUniswap } from '@/store/defi/uniswap';
import { useStore } from '@/store/utils';

export const assetsApi = (): AssetsApi => {
  const { getAssetInfo, getAssetIdentifierForSymbol } = useAssetInfoRetrieval();
  return {
    assetInfo: getAssetInfo,
    getIdentifierForSymbol: getAssetIdentifierForSymbol
  };
};

export const statisticsApi = (): StatisticsApi => {
  const store = useStore();
  const { isAssetIgnored } = useIgnoredAssetsStore();
  return {
    async assetValueDistribution(): Promise<TimedAssetBalances> {
      return api.queryLatestAssetValueDistribution();
    },
    async locationValueDistribution(): Promise<LocationData> {
      return api.queryLatestLocationValueDistribution();
    },
    async ownedAssets(): Promise<OwnedAssets> {
      const owned = await api.assets.queryOwnedAssets();
      return owned.filter(asset => !get(isAssetIgnored(asset)));
    },
    async timedBalances(
      asset: string,
      start: number,
      end: number
    ): Promise<TimedBalances> {
      return api.queryTimedBalancesData(asset, start, end);
    },
    async fetchNetValue(): Promise<void> {
      await store.dispatch('statistics/fetchNetValue');
    },
    netValue: startingDate =>
      computed(() => store.getters['statistics/netValue'](startingDate))
  };
};

export const userSettings = (): UserSettingsApi => {
  const store = useStore();
  return {
    floatingPrecision: computed<number>(
      () => store.getters['session/floatingPrecision']
    ),
    currencySymbol: computed<string>(
      () => store.getters['session/currencySymbol']
    ),
    shouldShowAmount: computed<boolean>(
      () => store.getters['session/shouldShowAmount']
    ),
    shouldShowPercentage: computed<boolean>(
      () => store.getters['session/shouldShowPercentage']
    ),
    scrambleData: computed<boolean>(
      () => (store.state as any).session.scrambleData
    ),
    darkModeEnabled: computed<boolean>(() => {
      return store.getters['settings/darkModeEnabled'];
    }),
    dateInputFormat: computed<string>(() => {
      return store.getters['settings/dateInputFormat'];
    }),
    graphZeroBased: computed(() => {
      const state = store.state;
      if (state.settings && state.settings.graphZeroBased) {
        return state.settings.graphZeroBased;
      }
      return false;
    }),
    privacyMode: computed<boolean>(() => store.getters['session/privacyMode'])
  };
};

export const adexApi = (): AdexApi => {
  const store = useStore();
  return {
    async fetchAdex(refresh: boolean) {
      await store.dispatch('staking/fetchAdex', refresh);
    },
    adexHistory: computed<AdexHistory>(() => {
      return (store.state as any).staking.adexHistory;
    }),
    adexBalances: computed<AdexBalances>(() => {
      return (store.state as any).staking.adexBalances;
    })
  };
};

export const balancesApi = (): BalancesApi => {
  const store = useStore();
  return {
    byLocation: computed<Record<string, BigNumber>>(() => {
      return store.getters['balances/byLocation'];
    }),
    aggregatedBalances: computed<AssetBalanceWithPrice[]>(() => {
      return store.getters['balances/aggregatedBalances'];
    }),
    exchangeRate: currency =>
      computed(() => store.getters['balances/exchangeRate'](currency))
  };
};

export const balancerApi = (): BalancerApi => {
  const store = useStore();
  return {
    balancerProfitLoss: (addresses: string[]) =>
      computed<BalancerProfitLoss[]>(() =>
        store.getters['defi/balancerProfitLoss'](addresses)
      ),
    balancerEvents: (addresses: string[]) =>
      computed<BalancerEvent[]>(() =>
        store.getters['defi/balancerEvents'](addresses)
      ),
    balancerBalances: computed<BalancerBalanceWithOwner[]>(
      () => store.getters['defi/balancerBalances']
    ),
    balancerPools: computed<Pool[]>(() => store.getters['defi/balancerPools']),
    balancerAddresses: computed<string[]>(
      () => store.getters['defi/balancerAddresses']
    ),
    fetchBalancerBalances: async (refresh: boolean) => {
      return await store.dispatch('defi/fetchBalancerBalances', refresh);
    },
    fetchBalancerEvents: async (refresh: boolean) => {
      return await store.dispatch('defi/fetchBalancerEvents', refresh);
    }
  };
};

export const compoundApi = (): CompoundApi => {
  const store = useStore();
  return {
    compoundRewards: computed<ProfitLossModel[]>(
      () => store.getters['defi/compoundRewards']
    ),
    compoundDebtLoss: computed<ProfitLossModel[]>(
      () => store.getters['defi/compoundDebtLoss']
    ),
    compoundLiquidationProfit: computed<ProfitLossModel[]>(
      () => store.getters['defi/compoundLiquidationProfit']
    ),
    compoundInterestProfit: computed<ProfitLossModel[]>(
      () => store.getters['defi/compoundInterestProfit']
    )
  };
};

export const dexTradeApi = (): DexTradesApi => {
  const store = useStore();
  const { fetchTrades: fetchUniswapTrades } = useUniswap();
  const { fetchTrades: fetchSushiswapTrades } = useSushiswapStore();
  return {
    dexTrades: addresses =>
      computed(() => store.getters['defi/dexTrades'](addresses)),
    fetchBalancerTrades: refresh =>
      store.dispatch('defi/fetchBalancerTrades', refresh),
    fetchSushiswapTrades,
    fetchUniswapTrades
  };
};

export const sushiApi = (): SushiApi => {
  const store = useSushiswapStore();
  const { addresses, pools } = toRefs(store);

  const { balanceList, eventList, fetchBalances, fetchEvents, poolProfit } =
    store;
  return {
    addresses,
    pools,
    events: eventList,
    balances: balanceList,
    poolProfit,
    fetchEvents,
    fetchBalances
  };
};

export const utilsApi = (): UtilsApi => {
  return {
    truncate: truncateAddress
  };
};
