import { type AssetBalanceWithPrice, type BigNumber } from '@rotki/common';
import { type ProfitLossModel } from '@rotki/common/lib/defi';
import {
  type AssetsApi,
  type BalancerApi,
  type BalancesApi,
  type CompoundApi,
  type StatisticsApi,
  type SushiApi,
  type UserSettingsApi,
  type UtilsApi
} from '@rotki/common/lib/premium';
import {
  type LocationData,
  type OwnedAssets,
  type TimedAssetBalances,
  type TimedBalances
} from '@rotki/common/lib/statistics';
import { type MaybeRef } from '@vueuse/core';
import { type ComputedRef } from 'vue';
import { truncateAddress } from '@/filters';
import { api } from '@/services/rotkehlchen-api';
import { useStatisticsApi } from '@/services/statistics/statistics-api';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
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
import { useStatisticsStore } from '@/store/statistics';
import { One } from '@/utils/bignumbers';
import { isNft } from '@/utils/nft';

export const assetsApi = (): AssetsApi => {
  const { assetInfo, assetSymbol, assetName, tokenAddress } =
    useAssetInfoRetrieval();

  return {
    assetInfo,
    assetSymbol: (identifier: MaybeRef<string>) =>
      computed(() => {
        if (isNft(get(identifier))) {
          return get(assetName(identifier));
        }
        return get(assetSymbol(identifier));
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
  const { privacyMode, scrambleData, shouldShowAmount, shouldShowPercentage } =
    storeToRefs(useSessionSettingsStore());
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
    selectedTheme,
    dateInputFormat,
    graphZeroBased,
    showGraphRangeSelector,
    privacyMode,
    scrambleData,
    shouldShowAmount,
    shouldShowPercentage
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
    getPoolName: useLiquidityPosition().getPoolName
  };
};
