import type { AggregationContext, AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import { addBalanceEntry } from '@/modules/balances/aggregation/core/balance-entry';

type ListingContext = Pick<AggregationContext, 'isAssetIgnored' | 'resolveIdentifier'>;

/**
 * Whether an asset shows in the balance tables: under its resolved identifier, it is not ignored.
 *
 * @remarks
 * The rule {@link mergeSources} applies, which inlines it to resolve each identifier only once.
 */
export function isListedAsset(asset: string, context: ListingContext): boolean {
  return !context.isAssetIgnored(context.resolveIdentifier(asset));
}

/**
 * Merges normalised sources into one set keyed by resolved identifier.
 *
 * @remarks
 * Two identifiers that resolve to the same asset are merged, so `ETH2` held on-chain and `ETH` held
 * on an exchange end up as one entry when the user treats them as the same asset.
 */
export function mergeSources(
  sources: readonly AssetBalanceEntries[],
  context: ListingContext,
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
