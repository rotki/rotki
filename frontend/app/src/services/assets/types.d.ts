import { CONFLICT_RESOLUTION } from '@/services/assets/consts';

export interface UnderlyingToken {
  readonly address: string;
  readonly weight: string;
}

export interface EthereumToken {
  readonly identifier?: string;
  readonly address: string;
  readonly decimals: number;
  readonly name: string;
  readonly symbol: string;
  readonly started?: number;
  readonly coingecko?: string | null;
  readonly cryptocompare?: string;
  readonly underlyingTokens?: UnderlyingToken[];
  readonly swappedFor?: string;
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
