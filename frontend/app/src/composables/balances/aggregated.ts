import type { Balances } from '@/types/blockchain/accounts';
import type { AssetProtocolBalances, EthBalance, ProtocolBalances } from '@/types/blockchain/balances';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { AssetPriceInfo } from '@/types/prices';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useCollectionInfo } from '@/modules/assets/use-collection-info';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { samePriceAssets } from '@/types/blockchain';
import { sortDesc, zeroBalance } from '@/utils/bignumbers';
import { balanceSum, perProtocolBalanceSum } from '@/utils/calculation';
import {
  assert,
  type AssetBalanceWithPrice,
  type Balance,
  type BigNumber,
  type ExclusionSource,
  type ProtocolBalance,
  Zero,
} from '@rotki/common';
import { omit } from 'es-toolkit';

type BalanceWithManual = Balance & { containsManual?: boolean };

type ProtocolBalancesWithManual = Record<string, BalanceWithManual>;

type AssetProtocolBalancesWithManual = Record<string, ProtocolBalancesWithManual>;

type SummarySource = 'manual' | 'blockchain' | 'exchanges';

interface UseAggregatedBalancesReturn {
  balances: (hideIgnored?: boolean, groupMultiChain?: boolean, exclude?: ExclusionSource[]) => ComputedRef<AssetBalanceWithPrice[]>;
  liabilities: (hideIgnored?: boolean) => ComputedRef<AssetBalanceWithPrice[]>;
  assetPriceInfo: (identifier: MaybeRef<string>, groupCollection?: MaybeRef<boolean>) => ComputedRef<AssetPriceInfo>;
  assets: ComputedRef<string[]>;
}

interface IntermediateGroupRepresentation {
  asset: string;
  isMain?: boolean;
  perProtocol: ProtocolBalances;
  usdValue: BigNumber;
  amount: BigNumber;
  usdPrice: BigNumber;
}

function manualToAssetProtocolBalances(balances: ManualBalanceWithValue[]): AssetProtocolBalances {
  const protocolBalances: AssetProtocolBalances = {};

  for (const { amount, asset, location, usdValue } of balances) {
    const balance: Balance = { amount, usdValue };

    protocolBalances[asset] ??= {};

    protocolBalances[asset][location] = protocolBalances[asset][location]
      ? balanceSum(protocolBalances[asset][location], balance)
      : balance;
  }
  return protocolBalances;
}

function blockchainToAssetProtocolBalances(balances: Balances, key: keyof EthBalance = 'assets'): AssetProtocolBalances {
  const aggregatedProtocolBalances: AssetProtocolBalances = {};

  for (const chainBalances of Object.values(balances)) {
    for (const accountBalances of Object.values(chainBalances)) {
      for (const [asset, protocolBalances] of Object.entries(accountBalances[key])) {
        aggregatedProtocolBalances[asset] ??= {};

        for (const [location, balance] of Object.entries(protocolBalances)) {
          aggregatedProtocolBalances[asset][location] = aggregatedProtocolBalances[asset][location]
            ? balanceSum(aggregatedProtocolBalances[asset][location], balance)
            : balance;
        }
      }
    }
  }

  return aggregatedProtocolBalances;
}

// Helper functions for better maintainability
function aggregateBalanceForProtocol(
  existingBalance: BalanceWithManual | undefined,
  newBalance: Balance,
  isManualSource: boolean,
): BalanceWithManual {
  if (!existingBalance) {
    return isManualSource
      ? { ...newBalance, containsManual: true }
      : newBalance;
  }

  const summedBalance = balanceSum(existingBalance, newBalance);
  const shouldMarkAsManual = isManualSource || existingBalance.containsManual;

  return shouldMarkAsManual
    ? { ...summedBalance, containsManual: true }
    : summedBalance;
}

function aggregateSourceBalances(
  sources: Record<SummarySource, AssetProtocolBalances>,
  associatedAssets: Record<string, string>,
  isAssetIgnored: (identifier: string) => boolean,
  hideIgnored: boolean,
): AssetProtocolBalancesWithManual {
  const aggregatedBalances: AssetProtocolBalancesWithManual = {};

  for (const [sourceType, source] of Object.entries(sources)) {
    const isManualSource = sourceType === 'manual';

    for (const asset in source) {
      const identifier = associatedAssets[asset] ?? asset;
      if (isAssetIgnored(identifier) && hideIgnored) {
        continue;
      }

      if (!aggregatedBalances[identifier]) {
        aggregatedBalances[identifier] = {};
      }

      for (const [protocol, balance] of Object.entries(source[asset])) {
        aggregatedBalances[identifier][protocol] = aggregateBalanceForProtocol(
          aggregatedBalances[identifier][protocol],
          balance,
          isManualSource,
        );
      }
    }
  }

  return aggregatedBalances;
}

function getSortedProtocolBalances(protocolBalances: ProtocolBalancesWithManual): ProtocolBalance[] {
  return Object.entries(protocolBalances)
    .filter(([, balance]) => balance.amount.gt(0))
    .map(([protocol, balance]) => ({
      protocol,
      ...balance,
    }))
    .sort((a, b) => {
      const usdValueComparison = sortDesc(a.usdValue, b.usdValue);
      if (usdValueComparison === 0) {
        return a.protocol.localeCompare(b.protocol);
      }
      return usdValueComparison;
    });
}

function createAssetBalanceFromAggregated(
  asset: string,
  protocolBalances: ProtocolBalancesWithManual,
  getAssetPrice: (asset: string, defaultValue: BigNumber) => BigNumber,
): AssetBalanceWithPrice {
  const assetTotal = perProtocolBalanceSum(zeroBalance(), protocolBalances);
  return {
    asset,
    usdPrice: getAssetPrice(asset, Zero),
    ...assetTotal,
    perProtocol: getSortedProtocolBalances(protocolBalances),
  } satisfies AssetBalanceWithPrice;
}

function processCollectionGrouping(
  aggregatedBalances: AssetProtocolBalancesWithManual,
  useCollectionId: (asset: string) => ComputedRef<string | undefined>,
  useCollectionMainAsset: (collectionId: string) => ComputedRef<string | undefined>,
  getAssetPrice: (asset: string, defaultValue: BigNumber) => BigNumber,
): AssetBalanceWithPrice[] {
  const grouped: Record<string, IntermediateGroupRepresentation[]> = {};
  const collectionCache = new Map<string, string | undefined>();

  // Group assets by collection
  for (const [asset, protocolBalances] of Object.entries(aggregatedBalances)) {
    const collectionId = get(useCollectionId(asset));
    const groupId = collectionId ? `collection-${collectionId}` : asset;

    // Cache main asset lookup to avoid repeated get() calls
    let mainAsset: string | undefined;
    if (collectionId) {
      if (!collectionCache.has(collectionId)) {
        collectionCache.set(collectionId, get(useCollectionMainAsset(collectionId)));
      }
      mainAsset = collectionCache.get(collectionId);
    }

    if (!grouped[groupId]) {
      grouped[groupId] = [];
    }

    const assetTotal = perProtocolBalanceSum(zeroBalance(), protocolBalances);
    grouped[groupId].push({
      asset,
      perProtocol: protocolBalances,
      ...assetTotal,
      usdPrice: getAssetPrice(asset, Zero),
      ...(mainAsset === asset ? { isMain: true } : {}),
    });
  }

  return Object.entries(grouped).map(([groupId, groupAssets]) => {
    // Handle collections that need main asset creation
    if (groupId.startsWith('collection-')) {
      const collectionId = groupId.replace('collection-', '');
      const mainAsset = collectionCache.get(collectionId);

      if (mainAsset && !groupAssets.some(value => value.asset === mainAsset)) {
        const zeroBalanceTotal = zeroBalance();
        groupAssets.push({
          asset: mainAsset,
          isMain: true,
          perProtocol: {},
          ...zeroBalanceTotal,
          usdPrice: getAssetPrice(mainAsset, Zero),
        });
      }
    }

    // Early return for single assets to avoid unnecessary processing
    if (groupAssets.length === 1) {
      const asset = groupAssets[0];
      const filteredAsset = omit(asset, ['isMain']);
      return {
        ...filteredAsset,
        perProtocol: getSortedProtocolBalances(filteredAsset.perProtocol),
      };
    }

    // Find main asset for multi-asset groups
    const main = groupAssets.find(value => value.isMain);
    assert(main);

    // Calculate group totals more efficiently
    let groupAmount = Zero;
    let groupUsdValue = Zero;
    const groupProtocolBalances: Record<string, Balance> = {};

    for (const asset of groupAssets) {
      groupAmount = groupAmount.plus(asset.amount);
      groupUsdValue = groupUsdValue.plus(asset.usdValue);

      for (const [protocol, balance] of Object.entries(asset.perProtocol)) {
        groupProtocolBalances[protocol] = groupProtocolBalances[protocol]
          ? balanceSum(groupProtocolBalances[protocol], balance)
          : balance;
      }
    }

    const filteredAsset = omit(main, ['isMain']);
    return {
      ...filteredAsset,
      amount: groupAmount,
      breakdown: groupAssets
        .filter(value => value.amount.gt(0))
        .map(value => ({
          ...omit(value, ['isMain']),
          perProtocol: getSortedProtocolBalances(value.perProtocol),
        })),
      perProtocol: getSortedProtocolBalances(groupProtocolBalances),
      usdValue: groupUsdValue,
    } satisfies AssetBalanceWithPrice;
  });
}

export function useAggregatedBalances(): UseAggregatedBalancesReturn {
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { getAssetPrice } = usePriceUtils();
  const { balances: exchangeBalances } = useExchangeData();
  const { balances: blockchainBalances, manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());

  const { assetAssociationMap } = useAssetInfoRetrieval();
  const { useCollectionId, useCollectionMainAsset } = useCollectionInfo();

  function summarizeAssetProtocols(
    sources: Record<SummarySource, AssetProtocolBalances>,
    associatedAssets: Record<string, string>,
    hideIgnored: boolean,
    groupCollections: boolean = true,
  ): AssetBalanceWithPrice[] {
    const aggregatedBalances = aggregateSourceBalances(
      sources,
      associatedAssets,
      isAssetIgnored,
      hideIgnored,
    );

    if (!groupCollections) {
      return Object.entries(aggregatedBalances)
        .map(([asset, protocolBalances]) =>
          createAssetBalanceFromAggregated(asset, protocolBalances, getAssetPrice),
        )
        .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
    }

    return processCollectionGrouping(
      aggregatedBalances,
      useCollectionId,
      useCollectionMainAsset,
      getAssetPrice,
    );
  }

  const balances = (
    hideIgnored = true,
    groupCollections = true,
    exclude: ExclusionSource[] = [],
  ): ComputedRef<AssetBalanceWithPrice[]> =>
    computed<AssetBalanceWithPrice[]>(() => {
      const exchange: AssetProtocolBalances = get(exchangeBalances);
      const manual: AssetProtocolBalances = manualToAssetProtocolBalances(get(manualBalances));
      const blockchain: AssetProtocolBalances = blockchainToAssetProtocolBalances(get(blockchainBalances));
      const associatedAssets = get(assetAssociationMap);

      const allSources = {
        blockchain,
        exchanges: exchange,
        manual,
      };

      const filteredSources = Object.entries(allSources)
        .filter(([key]) => !exclude.includes(key as ExclusionSource))
        .reduce((acc, [key, value]) => {
          acc[key as SummarySource] = get(value);
          return acc;
        }, {} as Record<SummarySource, AssetProtocolBalances>);

      return summarizeAssetProtocols(filteredSources, associatedAssets, hideIgnored, groupCollections);
    });

  const liabilities = (hideIgnored = true): ComputedRef<AssetBalanceWithPrice[]> =>
    computed<AssetBalanceWithPrice[]>(() => {
      const sources = {
        blockchain: blockchainToAssetProtocolBalances(get(blockchainBalances), 'liabilities'),
        exchanges: {},
        manual: manualToAssetProtocolBalances(get(manualLiabilities)),
      };
      const associatedAssets = get(assetAssociationMap);
      return summarizeAssetProtocols(sources, associatedAssets, hideIgnored);
    });

  const assets = computed<string[]>(() => {
    const assetSet = new Set<string>();

    const processAsset = (asset: string): void => {
      assetSet.add(asset);
      const samePrices = samePriceAssets[asset];
      if (samePrices)
        samePrices.forEach(asset => assetSet.add(asset));
    };

    const processAssetBalances = (balances: AssetProtocolBalances): void => {
      Object.keys(balances).forEach(processAsset);
    };

    processAssetBalances(blockchainToAssetProtocolBalances(get(blockchainBalances)));
    processAssetBalances(blockchainToAssetProtocolBalances(get(blockchainBalances), 'liabilities'));
    processAssetBalances(get(exchangeBalances));

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
      usdValue: assetValue?.usdValue ?? Zero,
    };
  });

  return {
    assetPriceInfo,
    assets,
    balances,
    liabilities,
  };
}
