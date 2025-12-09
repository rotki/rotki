import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { AssetBalances } from '@/types/balances';
import type { Balances } from '@/types/blockchain/accounts';
import type { AssetProtocolBalances } from '@/types/blockchain/balances';
import type { ExchangeInfo } from '@/types/exchanges';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import { computed, type ComputedRef } from 'vue';
import { summarizeAssetProtocols } from '@/composables/balances/asset-summary';
import { blockchainToAssetProtocolBalances, manualToAssetProtocolBalances } from '@/composables/balances/balance-transformations';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/data/defaults';
import { aggregateTotals } from '@/utils/blockchain/accounts';

/**
 * Gets blockchain location breakdown
 */
export function getBlockchainLocationBreakdown(
  balances: Balances,
  assetAssociationMap: Record<string, string>,
  skipIdentifier: (asset: string) => boolean,
): AssetBalances {
  return aggregateTotals(balances, 'assets', {
    assetAssociationMap,
    skipIdentifier,
  });
}

/**
 * Gets exchange balances by location (values already in main currency)
 */
export function getExchangeByLocationBalances(
  exchanges: ExchangeInfo[],
): Record<string, BigNumber> {
  const balances: Record<string, BigNumber> = {};
  for (const { location, total } of exchanges) {
    const balance = balances[location];
    balances[location] = !balance ? total : total.plus(balance);
  }
  return balances;
}

/**
 * Hook for getting location breakdown
 */
export function useLocationBreakdown(
  location: MaybeRef<string>,
  blockchainBalances: MaybeRef<Balances>,
  assetAssociationMap: MaybeRef<Record<string, string>>,
  manualBalances: MaybeRef<ManualBalanceWithValue[]>,
  useBaseExchangeBalances: (exchange?: MaybeRef<string>) => MaybeRef<AssetProtocolBalances>,
  isAssetIgnored: (identifier: string) => boolean,
  useCollectionId: (asset: string) => { value: string | undefined },
  useCollectionMainAsset: (collectionId: string) => { value: string | undefined },
  getAssetPrice: (asset: string, defaultValue: BigNumber) => BigNumber,
  noPrice: BigNumber,
): ComputedRef<AssetBalanceWithPrice[]> {
  return computed<AssetBalanceWithPrice[]>(() => {
    const selectedLocation = get(location);
    const associatedAssets = get(assetAssociationMap);

    const sources: Record<string, AssetProtocolBalances> = {
      blockchain: selectedLocation === TRADE_LOCATION_BLOCKCHAIN
        ? blockchainToAssetProtocolBalances(get(blockchainBalances))
        : {},
      exchanges: selectedLocation === TRADE_LOCATION_BLOCKCHAIN
        ? {}
        : get(useBaseExchangeBalances(selectedLocation)),
      manual: manualToAssetProtocolBalances(
        get(manualBalances).filter(balance => balance.location === selectedLocation),
      ),
    };

    return summarizeAssetProtocols({ associatedAssets, sources }, { hideIgnored: true, isAssetIgnored }, {
      getAssetPrice,
      noPrice,
    }, {
      groupCollections: true,
      useCollectionId,
      useCollectionMainAsset,
    });
  });
}
