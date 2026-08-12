import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { assetSuggestions } from '@/modules/core/common/display/assets';
import { toAssetField } from '@/modules/core/table/filters/shared/asset-field';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';

/** The two keys the historic prices table filters on, and the shape `useHistoricPrices` reads. */
export const HistoricPriceFilterKeys = {
  FROM_ASSET: 'fromAsset',
  TO_ASSET: 'toAsset',
} as const;

/**
 * The pill-bar fields for the historic prices table: the pair a price is quoted for.
 *
 * Both were `AssetSelect`s above the table, which is the same picker the asset pill carries — the
 * difference is that a pill says which side of the pair it is and can be removed, where an empty
 * select still occupied half the toolbar. The oracle prices tab already reads this way, so the
 * three price tabs now speak one language.
 */
export function useHistoricPriceFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  // Asset resolution is the same for every table filtering on one, so it comes from one place.
  const shared = useSharedFieldResolvers();
  const { assetSearch } = useAssetInfoRetrieval();

  // Built once: the search is debounced, and rebuilding it would hand each keystroke a fresh timer
  // that cancels nothing.
  const searchAsset = assetSuggestions(assetSearch);

  return [
    toAssetField({
      key: HistoricPriceFilterKeys.FROM_ASSET,
      label: (): string => t('price_management.from_asset'),
      searchAsset,
    }, shared),
    toAssetField({
      key: HistoricPriceFilterKeys.TO_ASSET,
      label: (): string => t('price_management.to_asset'),
      searchAsset,
    }, shared),
  ];
}
