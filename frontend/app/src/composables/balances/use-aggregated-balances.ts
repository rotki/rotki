import type { AssetProtocolBalances, EthBalance } from '@/modules/balances/types/blockchain-balances';
import type { AssetPriceInfo } from '@/modules/prices/price-types';
import { type AssetBalanceWithPrice, type AssetBalanceWithPriceAndChains, type BigNumber, type ExclusionSource, NoPrice, Zero } from '@rotki/common';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type MaybeRefOrGetter } from 'vue';
import { useResolveAssetIdentifier } from '@/composables/assets/common';
import { summarizeAssetProtocols } from '@/composables/balances/asset-summary';
import { type AssetProtocolBalancesWithChains, blockchainToAssetProtocolBalances, manualToAssetProtocolBalances } from '@/composables/balances/balance-transformations';
import { getBlockchainLocationBreakdown, getExchangeByLocationBalances, useLocationBreakdown } from '@/composables/balances/location-breakdown';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useCollectionInfo } from '@/modules/assets/use-collection-info';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { bigNumberSum } from '@/modules/common/data/calculation';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/modules/common/defaults';
import { samePriceAssets } from '@/modules/onchain/blockchain-types';
import { usePriceUtils } from '@/modules/prices/use-price-utils';

interface UseAggregatedBalancesReturn {
  useBalances: (hideIgnored?: boolean, groupMultiChain?: boolean, exclude?: ExclusionSource[]) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  getBalances: (hideIgnored?: boolean, groupMultiChain?: boolean, exclude?: ExclusionSource[]) => AssetBalanceWithPriceAndChains[];
  useLiabilities: (hideIgnored?: boolean) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  getLiabilities: (hideIgnored?: boolean) => AssetBalanceWithPriceAndChains[];
  useAssetPriceInfo: (identifier: MaybeRefOrGetter<string>, groupCollection?: MaybeRefOrGetter<boolean>) => ComputedRef<AssetPriceInfo>;
  getAssetPriceInfo: (identifier: string, groupMultiChain?: boolean) => AssetPriceInfo;
  assets: ComputedRef<string[]>;
  useBlockchainBalances: (chains: MaybeRefOrGetter<string[]>, address?: MaybeRefOrGetter<string>, key?: keyof EthBalance) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  getExchangeBalances: (exchange?: string) => AssetBalanceWithPriceAndChains[];
  useExchangeBalances: (exchange?: MaybeRefOrGetter<string>) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  useLocationBreakdown: (location: MaybeRefOrGetter<string>) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  balancesByLocation: ComputedRef<Record<string, BigNumber>>;
}

export function useAggregatedBalances(): UseAggregatedBalancesReturn {
  const { isAssetIgnored } = useAssetsStore();
  const { getAssetPrice } = usePriceUtils();
  const { exchanges, getBaseExchangeBalances, useBaseExchangeBalances } = useExchangeData();
  const { balances: blockchainBalances, manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { manualBalanceByLocation } = useManualBalanceData();

  const resolveAssetIdentifier = useResolveAssetIdentifier();
  const { getCollectionId, getCollectionMainAsset } = useCollectionInfo();
  const baseExchangeBalances = useBaseExchangeBalances();

  const blockchainAssetBalances = computed<AssetProtocolBalancesWithChains>(() => blockchainToAssetProtocolBalances(get(blockchainBalances)));
  const blockchainLiabilityBalances = computed<AssetProtocolBalancesWithChains>(() => blockchainToAssetProtocolBalances(get(blockchainBalances), 'liabilities'));
  const manualAssetBalances = computed<AssetProtocolBalances>(() => manualToAssetProtocolBalances(get(manualBalances)));
  const manualLiabilityBalances = computed<AssetProtocolBalances>(() => manualToAssetProtocolBalances(get(manualLiabilities)));

  function getBalances(hideIgnored = true, groupCollections = true, exclude: ExclusionSource[] = []): AssetBalanceWithPriceAndChains[] {
    const sources = {
      blockchain: exclude.includes('blockchain') ? {} : get(blockchainAssetBalances),
      exchanges: exclude.includes('exchange') ? {} : get(baseExchangeBalances),
      manual: exclude.includes('manual') ? {} : get(manualAssetBalances),
    };

    return summarizeAssetProtocols({ resolveIdentifier: resolveAssetIdentifier, sources }, { hideIgnored, isAssetIgnored }, {
      getAssetPrice,
      noPrice: NoPrice,
    }, {
      groupCollections,
      getCollectionId,
      getCollectionMainAsset,
    });
  }

  function getLiabilities(hideIgnored = true): AssetBalanceWithPriceAndChains[] {
    const sources = {
      blockchain: get(blockchainLiabilityBalances),
      exchanges: {},
      manual: get(manualLiabilityBalances),
    };
    return summarizeAssetProtocols({ resolveIdentifier: resolveAssetIdentifier, sources }, { hideIgnored, isAssetIgnored }, {
      getAssetPrice,
      noPrice: NoPrice,
    }, {
      groupCollections: true,
      getCollectionId,
      getCollectionMainAsset,
    });
  }

  function getAssetPriceInfo(identifier: string, groupMultiChain = false): AssetPriceInfo {
    const assetValue = getBalances(true, groupMultiChain).find(
      (value: AssetBalanceWithPrice) => value.asset === identifier,
    );

    return {
      amount: assetValue?.amount ?? Zero,
      price: assetValue?.price ?? Zero,
      value: assetValue?.value ?? Zero,
    };
  }

  const useBalances = (
    hideIgnored = true,
    groupCollections = true,
    exclude: ExclusionSource[] = [],
  ): ComputedRef<AssetBalanceWithPriceAndChains[]> =>
    computed<AssetBalanceWithPriceAndChains[]>(() => getBalances(hideIgnored, groupCollections, exclude));

  const useLiabilities = (hideIgnored = true): ComputedRef<AssetBalanceWithPriceAndChains[]> =>
    computed<AssetBalanceWithPriceAndChains[]>(() => getLiabilities(hideIgnored));

  const useAssetPriceInfo = (
    identifier: MaybeRefOrGetter<string>,
    groupMultiChain: MaybeRefOrGetter<boolean> = false,
  ): ComputedRef<AssetPriceInfo> => computed<AssetPriceInfo>(() => getAssetPriceInfo(toValue(identifier), toValue(groupMultiChain)));

  const useBlockchainBalances = (
    chains: MaybeRefOrGetter<string[]> = [],
    address?: MaybeRefOrGetter<string>,
    key: keyof EthBalance = 'assets',
  ): ComputedRef<AssetBalanceWithPriceAndChains[]> => computed<AssetBalanceWithPriceAndChains[]>(() => {
    const selectedChains = toValue(chains);
    const filter = selectedChains.length > 0 ? selectedChains : undefined;
    const accountAddress = address ? toValue(address) : undefined;
    const blockchain = blockchainToAssetProtocolBalances(get(blockchainBalances), key, filter, accountAddress);
    return summarizeAssetProtocols({
      resolveIdentifier: resolveAssetIdentifier,
      sources: { blockchain, exchanges: {}, manual: {} },
    }, {
      hideIgnored: true,
      isAssetIgnored,
    }, {
      getAssetPrice,
      noPrice: NoPrice,
    }, {
      groupCollections: true,
      getCollectionId,
      getCollectionMainAsset,
    });
  });

  function getExchangeBalances(exchange?: string): AssetBalanceWithPriceAndChains[] {
    const exchangeData = getBaseExchangeBalances(exchange);
    return summarizeAssetProtocols({
      resolveIdentifier: resolveAssetIdentifier,
      sources: { blockchain: {}, exchanges: exchangeData, manual: {} },
    }, {
      hideIgnored: true,
      isAssetIgnored,
    }, {
      getAssetPrice,
      noPrice: NoPrice,
    }, {
      groupCollections: true,
      getCollectionId,
      getCollectionMainAsset,
    });
  }

  const useExchangeBalances = (
    exchange?: MaybeRefOrGetter<string>,
  ): ComputedRef<AssetBalanceWithPriceAndChains[]> => computed<AssetBalanceWithPriceAndChains[]>(() =>
    getExchangeBalances(exchange ? toValue(exchange) : undefined),
  );

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

    processAssetBalances(get(blockchainAssetBalances));
    processAssetBalances(get(blockchainLiabilityBalances));
    processAssetBalances(get(baseExchangeBalances));

    get(manualBalances).forEach(({ asset }) => processAsset(asset));
    get(manualLiabilities).forEach(({ asset }) => processAsset(asset));

    return Array.from(assetSet);
  });

  const balancesByLocation = computed<Record<string, BigNumber>>(() => {
    const blockchainAssets = getBlockchainLocationBreakdown(get(blockchainBalances), resolveAssetIdentifier, asset => isAssetIgnored(asset));
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
    assets,
    balancesByLocation,
    getAssetPriceInfo,
    getBalances,
    getExchangeBalances,
    getLiabilities,
    useAssetPriceInfo,
    useBalances,
    useLiabilities,
    useBlockchainBalances,
    useExchangeBalances,
    useLocationBreakdown: (location: MaybeRefOrGetter<string>) => useLocationBreakdown(
      location,
      blockchainBalances,
      resolveAssetIdentifier,
      manualBalances,
      useBaseExchangeBalances,
      isAssetIgnored,
      getCollectionId,
      getCollectionMainAsset,
      getAssetPrice,
      NoPrice,
    ),
  };
}
