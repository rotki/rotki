import {
  AssetInfo,
  AssetInfoWithTransformer,
  SupportedAsset
} from '@rotki/common/lib/data';
import { z } from 'zod';
import { type ApiPagination, type TablePagination } from '@/types/pagination';
import { CollectionCommonFields } from '@/types/collection';

export interface AssetDBVersion {
  readonly local: number;
  readonly remote: number;
  readonly newChanges: number;
}

export interface AssetUpdateCheckResult {
  readonly updateAvailable: boolean;
  readonly versions?: AssetDBVersion;
}

export interface AssetUpdateConflictResult {
  readonly identifier: string;
  readonly local: SupportedAsset;
  readonly remote: SupportedAsset;
}

export type AssetUpdateResult = AssetUpdateConflictResult[] | boolean;

export interface ApplyUpdateResult {
  readonly done: boolean;
  readonly conflicts?: AssetUpdateConflictResult[];
}

export interface AssetMergePayload {
  readonly sourceIdentifier: string;
  readonly targetIdentifier: string;
}

export const AssetInfoWithId = AssetInfo.merge(
  z.object({
    identifier: z.string().min(1)
  })
).transform((data: any) => {
  return {
    ...data,
    isCustomAsset: data.isCustomAsset || data.assetType === 'custom asset'
  };
});

export type AssetInfoWithId = z.infer<typeof AssetInfoWithId>;

export const AssetsWithId = z.array(AssetInfoWithId);

export type AssetsWithId = z.infer<typeof AssetsWithId>;

export const AssetMap = z.object({
  assetCollections: z.record(AssetInfo),
  assets: z.record(AssetInfoWithTransformer)
});

export type AssetMap = z.infer<typeof AssetMap>;

export interface AssetPagination extends ApiPagination<SupportedAsset> {
  assetType?: string;
  name?: string;
  symbol?: string;
  showUserOwnedAssetsOnly?: boolean;
  ignoredAssetsHandling?: string;
  identifiers?: string[];
}

export interface AssetPaginationOptions
  extends TablePagination<SupportedAsset> {
  name?: string;
  symbol?: string;
  showUserOwnedAssetsOnly?: boolean;
  ignoredAssetsHandling?: string;
}

export const defaultAssetPagination = (
  itemsPerPage: number
): AssetPaginationOptions => ({
  page: 1,
  itemsPerPage,
  sortBy: ['symbol' as keyof SupportedAsset],
  sortDesc: [false]
});

export const CustomAsset = z.object({
  identifier: z.string(),
  name: z.string(),
  customAssetType: z.string(),
  notes: z.string().nullish()
});

export type CustomAsset = z.infer<typeof CustomAsset>;

export const CustomAssets = CollectionCommonFields.extend({
  entries: z.array(CustomAsset)
});
export type CustomAssets = z.infer<typeof CustomAssets>;

export interface CustomAssetPagination extends ApiPagination<CustomAsset> {
  name?: string;
  identifier?: string;
  customAssetType?: string;
}

export interface CustomAssetPaginationOptions
  extends TablePagination<CustomAsset> {
  name?: string;
  identifier?: string;
  customAssetType?: string;
}

export const defaultCustomAssetPagination = (
  itemsPerPage: number
): CustomAssetPaginationOptions => ({
  page: 0,
  itemsPerPage,
  sortBy: ['name' as keyof CustomAsset],
  sortDesc: [false]
});

export type IgnoredAssetsHandlingType = 'none' | 'exclude' | 'show_only';

export const EvmNativeToken = ['ETH'];
export const isEvmNativeToken = (asset: string) => {
  return EvmNativeToken.includes(asset);
};

export interface AssetVersionUpdate {
  local: number;
  remote: number;
  changes: number;
  upToVersion: number;
}

export interface AssetIdResponse {
  readonly identifier: string;
}

export const RESOLVE_REMOTE = 'remote';
export const RESOLVE_LOCAL = 'local';
export const CONFLICT_RESOLUTION = [RESOLVE_REMOTE, RESOLVE_LOCAL] as const;
export const EVM_TOKEN = 'evm token';
export const CUSTOM_ASSET = 'custom asset';

export type ConflictResolutionStrategy = (typeof CONFLICT_RESOLUTION)[number];

export interface AssetUpdatePayload {
  readonly resolution?: ConflictResolution;
  readonly version: number;
}

export type ConflictResolution = Readonly<
  Record<string, ConflictResolutionStrategy>
>;
export const SupportedAssets = CollectionCommonFields.extend({
  entries: z.array(SupportedAsset)
});
export type SupportedAssets = z.infer<typeof SupportedAssets>;
