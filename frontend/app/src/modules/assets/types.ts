import type { ConflictResolutionStrategy, PaginationRequestPayload } from '@/modules/core/common/common-types';
import { AssetCollection, AssetInfoWithId, AssetInfoWithTransformer, SupportedAsset } from '@rotki/common';
import { z } from 'zod';
import { CollectionCommonFields } from '@/modules/core/common/collection';

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
  assetFlag?: AssetFlag;
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

const ignoredAssetsHandlingValues: string[] = Object.values(IgnoredAssetHandlingType);

/**
 * Whether a string is one of the three handling modes. Needed where the value arrives untyped —
 * from the filter bar's param bag or the URL — so an unknown one falls back to the default rather
 * than reaching the request.
 */
export function isIgnoredAssetsHandling(value: string): value is IgnoredAssetsHandlingType {
  return ignoredAssetsHandlingValues.includes(value);
}

export const AssetFlag = {
  REBASING: 'rebasing',
} as const;

export type AssetFlag = (typeof AssetFlag)[keyof typeof AssetFlag];

export const IgnoredAssetResponse = z.object({
  noAction: z.array(z.string()),
  successful: z.array(z.string()),
});

export type IgnoredAssetResponse = z.infer<typeof IgnoredAssetResponse>;

const EvmNativeToken = ['ETH'];

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

export const HYPERLIQUID_CORE_CHAIN = 'hyperliquid core';

export const HYPERLIQUID_TOKEN = 'hyperliquid token';

export const SOLANA_CHAIN = 'solana';

export const SOLANA_TOKEN = 'solana token';

export const CUSTOM_ASSET = 'custom asset';

export const NON_EVM_CHAIN_ASSET_TYPES: Readonly<Record<string, string | undefined>> = {
  [HYPERLIQUID_CORE_CHAIN]: HYPERLIQUID_TOKEN,
  [SOLANA_CHAIN]: SOLANA_TOKEN,
};

export function isSpammableAssetType(assetType?: string | null): boolean {
  // Hyperliquid Core tokens do not have protocol storage in the backend yet, so exposing the spam
  // actions would make them fail validation instead of marking the asset as spam.
  return assetType === EVM_TOKEN || assetType === SOLANA_TOKEN;
}

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
