import type { AggregationContext, AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import { addBalanceEntry } from '@/modules/balances/aggregation/core/balance-entry';

/**
 * Merges normalised sources into one set keyed by resolved identifier.
 *
 * @remarks
 * Two identifiers that resolve to the same asset are merged, so `ETH2` held on-chain and `ETH` held
 * on an exchange end up as one entry when the user treats them as the same asset.
 */
export function mergeSources(
  sources: readonly AssetBalanceEntries[],
  context: Pick<AggregationContext, 'isAssetIgnored' | 'resolveIdentifier'>,
  hideIgnored: boolean,
): AssetBalanceEntries {
  const merged: AssetBalanceEntries = {};

  for (const source of sources) {
    for (const [asset, protocols] of Object.entries(source)) {
      const identifier = context.resolveIdentifier(asset);
      if (hideIgnored && context.isAssetIgnored(identifier))
        continue;

      const assetEntries = merged[identifier] ??= {};
      for (const [protocol, entry] of Object.entries(protocols))
        addBalanceEntry(assetEntries, protocol, entry);
    }
  }

  return merged;
}
