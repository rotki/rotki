import { CONFLICT_RESOLUTION } from '@/services/assets/consts';
import { Nullable } from '@/types';

export interface UnderlyingToken {
  readonly address: string;
  readonly weight: string;
}

export interface BaseAsset {
  readonly identifier: string;
  readonly coingecko?: Nullable<string>;
  readonly cryptocompare?: string;
  readonly started?: Nullable<number>;
  readonly name: string;
  readonly symbol: string;
  readonly swappedFor?: Nullable<string>;
}

export interface SupportedAsset extends BaseAsset {
  readonly active?: boolean;
  readonly ended?: number | null;
  readonly decimals?: number | null;
  readonly assetType: string;
  readonly forked?: string | null;
  readonly ethereumAddress?: string | null;
}

export interface EthereumToken extends BaseAsset {
  readonly address: string;
  readonly decimals: number;
  readonly underlyingTokens?: UnderlyingToken[];
  readonly protocol?: string;
}

export interface AssetIdResponse {
  readonly identifier: string;
}

export type ConflictResolutionStrategy = typeof CONFLICT_RESOLUTION[number];

export interface AssetUpdatePayload {
  readonly resolution?: ConflictResolution;
  readonly version: number;
}

export interface ConflictResolution {
  readonly [assetId: string]: ConflictResolutionStrategy;
}

export type ManagedAsset = EthereumToken | SupportedAsset;
