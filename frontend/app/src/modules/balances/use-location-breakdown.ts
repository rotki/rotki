import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type { AssetBalances } from '@/modules/balances/types/balances';
import type { AssetProtocolBalances } from '@/modules/balances/types/blockchain-balances';
import type { ExchangeInfo } from '@/modules/balances/types/exchanges';
import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import { computed, type ComputedRef, type MaybeRefOrGetter } from 'vue';
import { aggregateTotals } from '@/modules/accounts/account-helpers';
import { summarizeAssetProtocols } from '@/modules/balances/asset-summary';
import { blockchainToAssetProtocolBalances, manualToAssetProtocolBalances } from '@/modules/balances/balance-transformations';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/modules/core/common/defaults';

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
  getCollectionId: (asset: string) => string | undefined,
  getCollectionMainAsset: (collectionId: string) => string | undefined,
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
      getCollectionId,
      getCollectionMainAsset,
    });
  });
}
