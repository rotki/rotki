import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { assetSuggestions } from '@/modules/core/common/display/assets';
import { toAssetField } from '@/modules/core/table/filters/shared/asset-field';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';

/** The two keys the existing-caches table filters on. Matched against the rows it already holds. */
export const OracleCacheFilterKeys = {
  FROM_ASSET: 'fromAsset',
  TO_ASSET: 'toAsset',
} as const;

/**
 * The pill-bar fields for the existing oracle caches table: the pair a cache was built for.
 *
 * The same two asset pills the historic prices tab carries, with this table's own labels. The bar
 * also replaces the clear button that sat beside the two selects — removing a pill is what clearing
 * one filter means, and `Clear all` is what the button did.
 */
export function useOracleCacheFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const shared = useSharedFieldResolvers();
  const { assetSearch } = useAssetInfoRetrieval();

  const searchAsset = assetSuggestions(assetSearch);

  return [
    toAssetField({
      key: OracleCacheFilterKeys.FROM_ASSET,
      label: (): string => t('price_management.from_asset'),
      searchAsset,
    }, shared),
    toAssetField({
      key: OracleCacheFilterKeys.TO_ASSET,
      label: (): string => t('price_management.to_asset'),
      searchAsset,
    }, shared),
  ];
}
