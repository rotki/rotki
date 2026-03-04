import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { AssetBalances } from '@/types/balances';
import type { Balances } from '@/types/blockchain/accounts';
import type { AssetProtocolBalances } from '@/types/blockchain/balances';
import type { ExchangeInfo } from '@/types/exchanges';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import { computed, type ComputedRef, type MaybeRefOrGetter } from 'vue';
import { summarizeAssetProtocols } from '@/composables/balances/asset-summary';
import { blockchainToAssetProtocolBalances, manualToAssetProtocolBalances } from '@/composables/balances/balance-transformations';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/data/defaults';
import { aggregateTotals } from '@/utils/blockchain/accounts';

/**
 * Gets blockchain location breakdown
 */
export function getBlockchainLocationBreakdown(
  balances: Balances,
  resolveIdentifier: (id: string) => string,
  skipIdentifier: (asset: string) => boolean,
): AssetBalances {
  return aggregateTotals(balances, 'assets', {
    resolveIdentifier,
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
  location: MaybeRefOrGetter<string>,
  blockchainBalances: MaybeRefOrGetter<Balances>,
  resolveIdentifier: (id: string) => string,
  manualBalances: MaybeRefOrGetter<ManualBalanceWithValue[]>,
  useBaseExchangeBalances: (exchange?: MaybeRefOrGetter<string>) => MaybeRefOrGetter<AssetProtocolBalances>,
  isAssetIgnored: (identifier: string) => boolean,
  useCollectionId: (asset: string) => { value: string | undefined },
  useCollectionMainAsset: (collectionId: string) => { value: string | undefined },
  getAssetPrice: (asset: string, defaultValue: BigNumber) => BigNumber,
  noPrice: BigNumber,
): ComputedRef<AssetBalanceWithPrice[]> {
  return computed<AssetBalanceWithPrice[]>(() => {
    const selectedLocation = toValue(location);

    const sources: Record<string, AssetProtocolBalances> = {
      blockchain: selectedLocation === TRADE_LOCATION_BLOCKCHAIN
        ? blockchainToAssetProtocolBalances(toValue(blockchainBalances))
        : {},
      exchanges: selectedLocation === TRADE_LOCATION_BLOCKCHAIN
        ? {}
        : toValue(useBaseExchangeBalances(selectedLocation)),
      manual: manualToAssetProtocolBalances(
        toValue(manualBalances).filter(balance => balance.location === selectedLocation),
      ),
    };

    return summarizeAssetProtocols({ resolveIdentifier, sources }, { hideIgnored: true, isAssetIgnored }, {
      getAssetPrice,
      noPrice,
    }, {
      groupCollections: true,
      useCollectionId,
      useCollectionMainAsset,
    });
  });
}
