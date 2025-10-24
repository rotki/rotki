import type { ConflictResolutionStrategy, PaginationRequestPayload } from '@/types/common';
import { AssetCollection, AssetInfoWithId, AssetInfoWithTransformer, SupportedAsset } from '@rotki/common';
import { z } from 'zod/v4';
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

export const AssetsWithId = z.array(AssetInfoWithId);

export type AssetsWithId = z.infer<typeof AssetsWithId>;

export const AssetMap = z.object({
  assetCollections: z.record(z.string(), AssetCollection),
  assets: z.record(z.string(), AssetInfoWithTransformer),
});

export type AssetMap = z.infer<typeof AssetMap>;

export interface AssetRequestPayload extends PaginationRequestPayload<SupportedAsset> {
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
  customAssetType: z.string(),
  identifier: z.string(),
  name: z.string(),
  notes: z.string().nullable(),
});

export type CustomAsset = z.infer<typeof CustomAsset>;

export const CustomAssets = CollectionCommonFields.extend({
  entries: z.array(CustomAsset),
});

export type CustomAssets = z.infer<typeof CustomAssets>;

export interface CustomAssetRequestPayload extends PaginationRequestPayload<CustomAsset> {
  name?: string;
  identifier?: string;
  customAssetType?: string;
}

export const IgnoredAssetHandlingType = {
  EXCLUDE: 'exclude',
  NONE: 'none',
  SHOW_ONLY: 'show_only',
} as const;

export type IgnoredAssetsHandlingType = (typeof IgnoredAssetHandlingType)[keyof typeof IgnoredAssetHandlingType];

export const IgnoredAssetResponse = z.object({
  noAction: z.array(z.string()),
  successful: z.array(z.string()),
});

export type IgnoredAssetResponse = z.infer<typeof IgnoredAssetResponse>;

export const EvmNativeToken = ['ETH'];

export function isEvmNativeToken(asset: string): boolean {
  return EvmNativeToken.includes(asset);
}

export interface AssetVersionUpdate {
  local: number;
  remote: number;
  changes: number;
  upToVersion: number;
}

export interface AssetIdResponse {
  readonly identifier: string;
}

export type ConflictResolution = Readonly<Record<string, ConflictResolutionStrategy>>;

export const EVM_TOKEN = 'evm token';

export const SOLANA_TOKEN = 'solana token';

export const SOLANA_CHAIN = 'solana';

export const CUSTOM_ASSET = 'custom asset';

export interface AssetUpdatePayload {
  readonly resolution?: ConflictResolution;
  readonly version: number;
}

export const SupportedAssets = CollectionCommonFields.extend({
  entries: z.array(SupportedAsset),
});

export type SupportedAssets = z.infer<typeof SupportedAssets>;

export const CexMappingDeletePayload = z.object({
  location: z.string().nullable(),
  locationSymbol: z.string(),
});

export type CexMappingDeletePayload = z.infer<typeof CexMappingDeletePayload>;

export const CexMapping = CexMappingDeletePayload.extend({
  asset: z.string(),
});

export type CexMapping = z.infer<typeof CexMapping>;

export interface CexMappingRequestPayload extends PaginationRequestPayload<CexMapping> {
  location?: string;
}

export const CexMappingCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(CexMapping),
});
