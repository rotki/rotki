import type { AggregationContext } from '@/modules/balances/aggregation/core/aggregation-types';
import { NoPrice } from '@rotki/common';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useCollectionInfo } from '@/modules/assets/use-collection-info';
import { useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';

/**
 * The app's lookups, wired as the ports the aggregation core reads.
 *
 * @remarks
 * Every member reads reactive state when called, so a `computed` that calls into the core with this
 * context tracks prices, ignored assets and collections without the core knowing about reactivity.
 */
export function useAggregationContext(): AggregationContext {
  const { isAssetIgnored } = useAssetsStore();
  const { getAssetPrice } = usePriceUtils();
  const { getCollectionId, getCollectionMainAsset } = useCollectionInfo();
  const resolveIdentifier = useResolveAssetIdentifier();

  return {
    collectionOf: getCollectionId,
    isAssetIgnored,
    mainAssetOf: getCollectionMainAsset,
    priceOf: asset => getAssetPrice(asset, NoPrice),
    resolveIdentifier,
  };
}
