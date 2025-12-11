import type { MaybeRef } from '@vueuse/core';
import type { EthBalance } from '@/types/blockchain/balances';
import type { AssetPriceInfo } from '@/types/prices';
import { type AssetBalanceWithPrice, type AssetBalanceWithPriceAndChains, type BigNumber, type ExclusionSource, NoPrice, Zero } from '@rotki/common';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, ref } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { summarizeAssetProtocols } from '@/composables/balances/asset-summary';
import { blockchainToAssetProtocolBalances, manualToAssetProtocolBalances } from '@/composables/balances/balance-transformations';
import { getBlockchainLocationBreakdown, getExchangeByLocationBalances, useLocationBreakdown } from '@/composables/balances/location-breakdown';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/data/defaults';
import { useCollectionInfo } from '@/modules/assets/use-collection-info';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { samePriceAssets } from '@/types/blockchain';
import { bigNumberSum } from '@/utils/calculation';

interface UseAggregatedBalancesReturn {
  balances: (hideIgnored?: boolean, groupMultiChain?: boolean, exclude?: ExclusionSource[]) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  liabilities: (hideIgnored?: boolean) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  assetPriceInfo: (identifier: MaybeRef<string>, groupCollection?: MaybeRef<boolean>) => ComputedRef<AssetPriceInfo>;
  assets: ComputedRef<string[]>;
  useBlockchainBalances: (chains: MaybeRef<string[]>, address?: MaybeRef<string>, key?: keyof EthBalance) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  useExchangeBalances: (exchange?: MaybeRef<string>) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  useLocationBreakdown: (location: MaybeRef<string>) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  balancesByLocation: ComputedRef<Record<string, BigNumber>>;
}

export function useAggregatedBalances(): UseAggregatedBalancesReturn {
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { getAssetPrice } = usePriceUtils();
  const { exchanges, useBaseExchangeBalances } = useExchangeData();
  const { balances: blockchainBalances, manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { manualBalanceByLocation } = useManualBalanceData();

  const { assetAssociationMap } = useAssetInfoRetrieval();
  const { useCollectionId, useCollectionMainAsset } = useCollectionInfo();

  const balances = (
    hideIgnored = true,
    groupCollections = true,
    exclude: ExclusionSource[] = [],
  ): ComputedRef<AssetBalanceWithPriceAndChains[]> =>
    computed<AssetBalanceWithPriceAndChains[]>(() => {
      const exchange = get(useBaseExchangeBalances());
      const manual = manualToAssetProtocolBalances(get(manualBalances));
      const blockchain = blockchainToAssetProtocolBalances(get(blockchainBalances));
      const associatedAssets = get(assetAssociationMap);

      const allSources = {
        blockchain,
        exchanges: exchange,
        manual,
      };

      const filteredSources = Object.entries(allSources)
        .filter(([key]) => !exclude.includes(key as ExclusionSource))
        .reduce((acc, [key, value]) => {
          acc[key as 'blockchain' | 'exchanges' | 'manual'] = value;
          return acc;
        }, {} as Record<'blockchain' | 'exchanges' | 'manual', typeof blockchain>);

      return summarizeAssetProtocols({ associatedAssets, sources: filteredSources }, { hideIgnored, isAssetIgnored }, {
        getAssetPrice,
        noPrice: NoPrice,
      }, {
        groupCollections,
        useCollectionId,
        useCollectionMainAsset,
      });
    });

  const liabilities = (hideIgnored = true): ComputedRef<AssetBalanceWithPriceAndChains[]> =>
    computed<AssetBalanceWithPriceAndChains[]>(() => {
      const sources = {
        blockchain: blockchainToAssetProtocolBalances(get(blockchainBalances), 'liabilities'),
        exchanges: {},
        manual: manualToAssetProtocolBalances(get(manualLiabilities)),
      };
      const associatedAssets = get(assetAssociationMap);
      return summarizeAssetProtocols({ associatedAssets, sources }, { hideIgnored, isAssetIgnored }, {
        getAssetPrice,
        noPrice: NoPrice,
      }, {
        groupCollections: true,
        useCollectionId,
        useCollectionMainAsset,
      });
    });

  const useBlockchainBalances = (
    chains: MaybeRef<string[]> = [],
    address?: MaybeRef<string>,
    key: keyof EthBalance = 'assets',
  ): ComputedRef<AssetBalanceWithPriceAndChains[]> => computed<AssetBalanceWithPriceAndChains[]>(() => {
    const selectedChains = get(chains);
    const filter = selectedChains.length > 0 ? selectedChains : undefined;
    const accountAddress = address ? get(address) : undefined;
    const blockchain = blockchainToAssetProtocolBalances(get(blockchainBalances), key, filter, accountAddress);
    return summarizeAssetProtocols({
      associatedAssets: get(assetAssociationMap),
      sources: { blockchain, exchanges: {}, manual: {} },
    }, {
      hideIgnored: true,
      isAssetIgnored,
    }, {
      getAssetPrice,
      noPrice: NoPrice,
    }, {
      groupCollections: true,
      useCollectionId,
      useCollectionMainAsset,
    });
  });

  const useExchangeBalances = (
    exchange?: MaybeRef<string>,
  ): ComputedRef<AssetBalanceWithPriceAndChains[]> => computed<AssetBalanceWithPriceAndChains[]>(() => {
    const exchanges = get(useBaseExchangeBalances(exchange));
    return summarizeAssetProtocols({
      associatedAssets: get(assetAssociationMap),
      sources: { blockchain: {}, exchanges, manual: {} },
    }, {
      hideIgnored: true,
      isAssetIgnored,
    }, {
      getAssetPrice,
      noPrice: NoPrice,
    }, {
      groupCollections: true,
      useCollectionId,
      useCollectionMainAsset,
    });
  });

  const assets = computed<string[]>(() => {
    const assetSet = new Set<string>();

    const processAsset = (asset: string): void => {
      assetSet.add(asset);
      const samePrices = samePriceAssets[asset];
      if (samePrices)
        samePrices.forEach(asset => assetSet.add(asset));
    };

    const processAssetBalances = (balances: Record<string, unknown>): void => {
      Object.keys(balances).forEach(processAsset);
    };

    processAssetBalances(blockchainToAssetProtocolBalances(get(blockchainBalances)));
    processAssetBalances(blockchainToAssetProtocolBalances(get(blockchainBalances), 'liabilities'));
    processAssetBalances(get(useBaseExchangeBalances()));

    get(manualBalances).forEach(({ asset }) => processAsset(asset));
    get(manualLiabilities).forEach(({ asset }) => processAsset(asset));

    return Array.from(assetSet);
  });

  const assetPriceInfo = (
    identifier: MaybeRef<string>,
    groupMultiChain: MaybeRef<boolean> = ref(false),
  ): ComputedRef<AssetPriceInfo> => computed<AssetPriceInfo>(() => {
    const id = get(identifier);
    const assetValue = get(balances(true, get(groupMultiChain))).find(
      (value: AssetBalanceWithPrice) => value.asset === id,
    );

    return {
      amount: assetValue?.amount ?? Zero,
      usdPrice: assetValue?.usdPrice ?? Zero,
      value: assetValue?.value ?? Zero,
    };
  });

  const balancesByLocation = computed<Record<string, BigNumber>>(() => {
    const blockchainAssets = getBlockchainLocationBreakdown(get(blockchainBalances), get(assetAssociationMap), asset => isAssetIgnored(asset));
    const blockchainTotal = bigNumberSum(Object.values(blockchainAssets).map(asset => asset.value));
    const map: Record<string, BigNumber> = {
      [TRADE_LOCATION_BLOCKCHAIN]: blockchainTotal,
    };

    const exchange = getExchangeByLocationBalances(get(exchanges));
    for (const location in exchange) {
      const total = map[location];
      const locationValue = exchange[location];
      map[location] = total ? total.plus(locationValue) : locationValue;
    }

    const manual = get(manualBalanceByLocation);
    for (const { location, value } of manual) {
      const total = map[location];
      map[location] = total ? total.plus(value) : value;
    }

    return map;
  });

  return {
    assetPriceInfo,
    assets,
    balances,
    balancesByLocation,
    liabilities,
    useBlockchainBalances,
    useExchangeBalances,
    useLocationBreakdown: (location: MaybeRef<string>) => useLocationBreakdown(
      location,
      blockchainBalances,
      assetAssociationMap,
      manualBalances,
      useBaseExchangeBalances,
      isAssetIgnored,
      useCollectionId,
      useCollectionMainAsset,
      getAssetPrice,
      NoPrice,
    ),
  };
}
