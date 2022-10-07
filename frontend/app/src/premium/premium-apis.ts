import { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import { AssetInfo } from '@rotki/common/lib/data';
import { ProfitLossModel } from '@rotki/common/lib/defi';
import {
  AdexApi,
  AssetsApi,
  BalancerApi,
  BalancesApi,
  CompoundApi,
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
import { MaybeRef } from '@vueuse/core';
import { ComputedRef, Ref } from 'vue';
import { setupLiquidityPosition } from '@/composables/defi';
import { truncateAddress } from '@/filters';
import { api } from '@/services/rotkehlchen-api';
import { useStatisticsApi } from '@/services/statistics/statistics-api';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useNftAssetInfoStore } from '@/store/assets/nft';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useAggregatedBalancesStore } from '@/store/balances/aggregated';
import { useBalancesBreakdownStore } from '@/store/balances/breakdown';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useBalancerStore } from '@/store/defi/balancer';
import { useCompoundStore } from '@/store/defi/compound';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useAdexStakingStore } from '@/store/staking';
import { useStatisticsStore } from '@/store/statistics';
import { One } from '@/utils/bignumbers';

export const assetsApi = (): AssetsApi => {
  const { assetInfo, assetSymbol, tokenAddress } = useAssetInfoRetrieval();

  const { getNftDetails } = useNftAssetInfoStore();

  return {
    assetInfo: (identifier: MaybeRef<string>) =>
      computed(() => {
        const nft = get(getNftDetails(identifier)) as AssetInfo | null;
        return nft ?? get(assetInfo(identifier));
      }),
    assetSymbol: (identifier: MaybeRef<string>) =>
      computed(() => {
        const nft = get(getNftDetails(identifier)) as AssetInfo | null;
        return nft?.symbol ?? get(assetSymbol(identifier));
      }),
    tokenAddress: (identifier: MaybeRef<string>) => tokenAddress(identifier)
  };
};

export const statisticsApi = (): StatisticsApi => {
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { fetchNetValue, getNetValue } = useStatisticsStore();
  const statsApi = useStatisticsApi();
  return {
    async assetValueDistribution(): Promise<TimedAssetBalances> {
      return statsApi.queryLatestAssetValueDistribution();
    },
    async locationValueDistribution(): Promise<LocationData> {
      return statsApi.queryLatestLocationValueDistribution();
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
      return statsApi.queryTimedBalancesData(asset, start, end);
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
  const { balancesByLocation } = storeToRefs(useBalancesBreakdownStore());
  const { balances } = useAggregatedBalancesStore();
  return {
    byLocation: balancesByLocation as ComputedRef<Record<string, BigNumber>>,
    aggregatedBalances: balances() as ComputedRef<AssetBalanceWithPrice[]>,
    exchangeRate: (currency: string) =>
      computed(() => get(exchangeRate(currency)) ?? One)
  };
};

export const balancerApi = (): BalancerApi => {
  const store = useBalancerStore();
  const { pools, addresses } = storeToRefs(store);
  return {
    balancerProfitLoss: (addresses: string[]) => store.profitLoss(addresses),
    balancerEvents: (addresses: string[]) => store.eventList(addresses),
    balancerBalances: (addresses: string[]) =>
      store.balancerBalances(addresses),
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
    truncate: truncateAddress,
    getPoolName: setupLiquidityPosition().getPoolName
  };
};
