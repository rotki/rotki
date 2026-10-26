import type { MatchedKeyword } from '@/modules/core/table/filtering';

/** The wire keys the custom assets table filters on, which the URL carries too. */
export const CustomAssetFilterKeys = {
  CUSTOM_ASSET_TYPE: 'custom_asset_type',
  NAME: 'name',
} as const;

type CustomAssetFilterKey = typeof CustomAssetFilterKeys[keyof typeof CustomAssetFilterKeys];

export type Filters = MatchedKeyword<CustomAssetFilterKey>;
