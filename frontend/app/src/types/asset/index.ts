import {
  AssetInfo,
  AssetInfoWithTransformer,
  SupportedAsset
} from '@rotki/common/lib/data';
import { z } from 'zod';
import {
  type ConflictResolutionStrategy,
  type PaginationRequestPayload
} from '@/types/common';
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
).transform((data: any) => ({
  ...data,
  isCustomAsset: data.isCustomAsset || data.assetType === 'custom asset'
}));

export type AssetInfoWithId = z.infer<typeof AssetInfoWithId>;

export const AssetsWithId = z.array(AssetInfoWithId);

export type AssetsWithId = z.infer<typeof AssetsWithId>;

export const AssetMap = z.object({
  assetCollections: z.record(AssetInfo),
  assets: z.record(AssetInfoWithTransformer)
});

export type AssetMap = z.infer<typeof AssetMap>;

export interface AssetRequestPayload
  extends PaginationRequestPayload<SupportedAsset> {
  assetType?: string;
  name?: string;
  symbol?: string;
  evmChain?: string;
  address?: string;
  showUserOwnedAssetsOnly?: boolean;
  showWhitelistedAssetsOnly?: boolean;
  ignoredAssetsHandling?: string;
  identifiers?: string[];
}

export const CustomAsset = z.object({
  identifier: z.string(),
  name: z.string(),
  customAssetType: z.string(),
  notes: z.string().nullable()
});

export type CustomAsset = z.infer<typeof CustomAsset>;

export const CustomAssets = CollectionCommonFields.extend({
  entries: z.array(CustomAsset)
});

export type CustomAssets = z.infer<typeof CustomAssets>;

export interface CustomAssetRequestPayload
  extends PaginationRequestPayload<CustomAsset> {
  name?: string;
  identifier?: string;
  customAssetType?: string;
}

export const IgnoredAssetHandlingType = {
  NONE: 'none',
  EXCLUDE: 'exclude',
  SHOW_ONLY: 'show_only'
} as const;

export type IgnoredAssetsHandlingType =
  (typeof IgnoredAssetHandlingType)[keyof typeof IgnoredAssetHandlingType];

export const EvmNativeToken = ['ETH'];

export const isEvmNativeToken = (asset: string) =>
  EvmNativeToken.includes(asset);

export interface AssetVersionUpdate {
  local: number;
  remote: number;
  changes: number;
  upToVersion: number;
}

export interface AssetIdResponse {
  readonly identifier: string;
}

export type ConflictResolution = Readonly<
  Record<string, ConflictResolutionStrategy>
>;

export const EVM_TOKEN = 'evm token';

export const CUSTOM_ASSET = 'custom asset';

export interface AssetUpdatePayload {
  readonly resolution?: ConflictResolution;
  readonly version: number;
}

export const SupportedAssets = CollectionCommonFields.extend({
  entries: z.array(SupportedAsset)
});

export type SupportedAssets = z.infer<typeof SupportedAssets>;
