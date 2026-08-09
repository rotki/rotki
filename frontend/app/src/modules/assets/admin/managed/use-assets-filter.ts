import type { MatchedKeyword } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import { FilterKeyArities, filterRouteSchema } from '@/modules/core/table/route';

/** The wire keys the managed assets table filters on, which the URL carries too. */
export const AssetFilterKeys = {
  ADDRESS: 'address',
  ASSET_FLAG: 'assetFlag',
  ASSET_TYPE: 'assetType',
  CHAIN: 'evmChain',
  IDENTIFIER: 'identifiers',
  NAME: 'name',
  SYMBOL: 'symbol',
} as const;

export type AssetFilterKey = typeof AssetFilterKeys[keyof typeof AssetFilterKeys];

export type Filters = MatchedKeyword<AssetFilterKey>;

export function useAssetFilter(): FilterSchema<Filters> {
  const modelFilters = ref<Filters>({});

  return {
    filters: modelFilters,
    RouteFilterSchema: filterRouteSchema({
      [AssetFilterKeys.ADDRESS]: FilterKeyArities.ONE,
      [AssetFilterKeys.ASSET_FLAG]: FilterKeyArities.ONE,
      [AssetFilterKeys.ASSET_TYPE]: FilterKeyArities.ONE,
      [AssetFilterKeys.CHAIN]: FilterKeyArities.ONE,
      [AssetFilterKeys.IDENTIFIER]: FilterKeyArities.MANY,
      [AssetFilterKeys.NAME]: FilterKeyArities.ONE,
      [AssetFilterKeys.SYMBOL]: FilterKeyArities.ONE,
    }),
  };
}
