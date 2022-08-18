import { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import { ProfitLossModel } from '@rotki/common/lib/defi';
import { BalancerBalanceWithOwner } from '@rotki/common/lib/defi/balancer';
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
import { computed, ComputedRef, Ref } from '@vue/composition-api';
import { get, toRefs } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { truncateAddress } from '@/filters';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval, useIgnoredAssetsStore } from '@/store/assets';
import { useBalancesStore } from '@/store/balances';
import { useBlockchainBalancesStore } from '@/store/balances/blockchain-balances';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useBalancerStore } from '@/store/defi/balancer';
import { useCompoundStore } from '@/store/defi/compound';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { useDexTradesStore } from '@/store/defi/trades';
import { useUniswapStore } from '@/store/defi/uniswap';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useAdexStakingStore } from '@/store/staking';
import { useStatisticsStore } from '@/store/statistics';
import { One } from '@/utils/bignumbers';

export const assetsApi = (): AssetsApi => {
  const { getAssetInfo, getAssetSymbol, getAssetIdentifierForSymbol } =
    useAssetInfoRetrieval();
  return {
    assetInfo: getAssetInfo,
    assetSymbol: getAssetSymbol,
    getIdentifierForSymbol: getAssetIdentifierForSymbol
  };
};

export const statisticsApi = (): StatisticsApi => {
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { fetchNetValue, getNetValue } = useStatisticsStore();
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
      await fetchNetValue();
    },
    netValue: startingDate => getNetValue(startingDate)
  };
};

export const userSettings = (): UserSettingsApi => {
  const sessionRefs = storeToRefs(useSessionSettingsStore());
  const { floatingPrecision, currencySymbol } = storeToRefs(
    useGeneralSettingsStore()
  );
  const {
    selectedTheme,
    dateInputFormat,
    graphZeroBased,
    showGraphRangeSelector
  } = storeToRefs(useFrontendSettingsStore());

  return {
    floatingPrecision,
    currencySymbol,
    ...sessionRefs,
    selectedTheme,
    dateInputFormat,
    graphZeroBased,
    showGraphRangeSelector
  };
};

export const adexApi = (): AdexApi => {
  const store = useAdexStakingStore();
  const { adexBalances, adexHistory } = storeToRefs(store);
  const { fetchAdex } = store;
  return {
    async fetchAdex(refresh: boolean) {
      await fetchAdex(refresh);
    },
    adexHistory: adexHistory as Ref<AdexHistory>,
    adexBalances: adexBalances as Ref<AdexBalances>
  };
};

export const balancesApi = (): BalancesApi => {
  const { exchangeRate } = useBalancePricesStore();
  const { balancesByLocation } = storeToRefs(useBalancesStore());
  const { aggregatedBalances } = storeToRefs(useBlockchainBalancesStore());
  return {
    byLocation: balancesByLocation as ComputedRef<Record<string, BigNumber>>,
    aggregatedBalances: aggregatedBalances as ComputedRef<
      AssetBalanceWithPrice[]
    >,
    exchangeRate: (currency: string) =>
      computed(() => get(exchangeRate(currency)) ?? One)
  };
};

export const balancerApi = (): BalancerApi => {
  const store = useBalancerStore();
  const { balanceList, pools, addresses } = storeToRefs(store);
  return {
    balancerProfitLoss: (addresses: string[]) => store.profitLoss(addresses),
    balancerEvents: (addresses: string[]) => store.eventList(addresses),
    balancerBalances: balanceList as Ref<BalancerBalanceWithOwner[]>,
    balancerPools: pools,
    balancerAddresses: addresses,
    fetchBalancerBalances: async (refresh: boolean) => {
      return await store.fetchBalances(refresh);
    },
    fetchBalancerEvents: async (refresh: boolean) => {
      return await store.fetchEvents(refresh);
    }
  };
};

type ProfitLossRef = ComputedRef<ProfitLossModel[]>;

export const compoundApi = (): CompoundApi => {
  const { rewards, debtLoss, interestProfit, liquidationProfit } = storeToRefs(
    useCompoundStore()
  );

  return {
    compoundRewards: rewards as ProfitLossRef,
    compoundDebtLoss: debtLoss as ProfitLossRef,
    compoundLiquidationProfit: liquidationProfit as ProfitLossRef,
    compoundInterestProfit: interestProfit as ProfitLossRef
  };
};

export const dexTradeApi = (): DexTradesApi => {
  const store = useDexTradesStore();
  const { fetchTrades: fetchUniswapTrades } = useUniswapStore();
  const { fetchTrades: fetchSushiswapTrades } = useSushiswapStore();
  const { fetchTrades: fetchBalancerTrades } = useBalancerStore();
  return {
    dexTrades: addresses => store.dexTrades(addresses),
    fetchBalancerTrades,
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
