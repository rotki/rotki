import type { AssetPriceInfo } from '@/modules/assets/prices/price-types';
import type { AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import type { EthBalance } from '@/modules/balances/types/blockchain-balances';
import { type AssetBalanceWithPrice, type AssetBalanceWithPriceAndChains, type BigNumber, type ExclusionSource, Zero } from '@rotki/common';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type MaybeRefOrGetter } from 'vue';
import { type BalanceInputs, locationSources } from '@/modules/balances/aggregation/core/location-sources';
import { fromBlockchain, fromExchanges, fromManual } from '@/modules/balances/aggregation/core/sources';
import { summarizeBalances } from '@/modules/balances/aggregation/core/summarize';
import { useAggregationContext } from '@/modules/balances/aggregation/use-aggregation-context';
import { samePriceAssets } from '@/modules/balances/blockchain-types';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { getBlockchainLocationBreakdown, getExchangeByLocationBalances } from '@/modules/balances/use-location-breakdown';
import { bigNumberSum } from '@/modules/core/common/data/calculation';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/modules/core/common/defaults';
import { useLocations } from '@/modules/core/common/use-locations';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

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
  balancesByChainLocation: ComputedRef<Record<string, BigNumber>>;
}

const EXCLUDABLE_SOURCES = ['blockchain', 'exchange', 'manual'] as const satisfies readonly ExclusionSource[];

export function useAggregatedBalances(): UseAggregatedBalancesReturn {
  const { exchanges } = useExchangeData();
  const { balances: blockchainBalances, exchangeBalances, manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { manualBalanceByLocation } = useManualBalanceData();
  const { tradeLocations } = useLocations();
  const { matchChain } = useSupportedChains();

  const context = useAggregationContext();
  const { isAssetIgnored, resolveIdentifier: resolveAssetIdentifier } = context;

  const blockchainAssets = computed<AssetBalanceEntries>(() => fromBlockchain(get(blockchainBalances)));
  const blockchainLiabilities = computed<AssetBalanceEntries>(() => fromBlockchain(get(blockchainBalances), { key: 'liabilities' }));
  const exchangeAssets = computed<AssetBalanceEntries>(() => fromExchanges(get(exchangeBalances)));
  const manualAssets = computed<AssetBalanceEntries>(() => fromManual(get(manualBalances)));
  const manualLiabilityEntries = computed<AssetBalanceEntries>(() => fromManual(get(manualLiabilities)));

  const assetSources: Record<ExclusionSource, ComputedRef<AssetBalanceEntries>> = {
    blockchain: blockchainAssets,
    exchange: exchangeAssets,
    manual: manualAssets,
  };

  function getBalances(hideIgnored = true, groupCollections = true, exclude: ExclusionSource[] = []): AssetBalanceWithPriceAndChains[] {
    const sources = EXCLUDABLE_SOURCES
      .filter(source => !exclude.includes(source))
      .map(source => get(assetSources[source]));
    return summarizeBalances(sources, context, { groupCollections, hideIgnored });
  }

  function getLiabilities(hideIgnored = true): AssetBalanceWithPriceAndChains[] {
    return summarizeBalances([get(blockchainLiabilities), get(manualLiabilityEntries)], context, { hideIgnored });
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
    const source = fromBlockchain(get(blockchainBalances), {
      address: address ? toValue(address) : undefined,
      chains: toValue(chains),
      key,
    });
    return summarizeBalances([source], context);
  });

  function getExchangeBalances(exchange?: string): AssetBalanceWithPriceAndChains[] {
    return summarizeBalances([fromExchanges(get(exchangeBalances), exchange)], context);
  }

  const useLocationBreakdown = (location: MaybeRefOrGetter<string>): ComputedRef<AssetBalanceWithPriceAndChains[]> =>
    computed<AssetBalanceWithPriceAndChains[]>(() => {
      const selected = toValue(location);
      const inputs: BalanceInputs = {
        blockchain: get(blockchainBalances),
        exchanges: get(exchangeBalances),
        manual: get(manualBalances),
      };
      return summarizeBalances(locationSources(selected, inputs, matchChain(selected)), context);
    });

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

    processAssetBalances(get(blockchainAssets));
    processAssetBalances(get(blockchainLiabilities));
    processAssetBalances(get(exchangeAssets));

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

  /**
   * On-chain totals per chain, keyed by trade-location identifier such as `ethereum`.
   *
   * @remarks
   * What makes a chain discoverable in global search. Kept apart from {@link balancesByLocation} so
   * that its umbrella `blockchain` aggregate stays authoritative for the premium consumers that
   * iterate that map.
   */
  const balancesByChainLocation = computed<Record<string, BigNumber>>(() => {
    const balances = get(blockchainBalances);
    const locations = get(tradeLocations);
    const result: Record<string, BigNumber> = {};
    for (const location of locations) {
      const chain = matchChain(location.identifier);
      if (!chain || !balances[chain])
        continue;
      const assets = getBlockchainLocationBreakdown(
        { [chain]: balances[chain] },
        resolveAssetIdentifier,
        asset => isAssetIgnored(asset),
      );
      const total = bigNumberSum(Object.values(assets).map(asset => asset.value));
      if (!total.isZero())
        result[location.identifier] = total;
    }
    return result;
  });

  return {
    assets,
    balancesByChainLocation,
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
    useLocationBreakdown,
  };
}
