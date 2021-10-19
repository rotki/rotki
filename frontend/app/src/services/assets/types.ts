import { AssetEntry, NumericString, BigNumber } from '@rotki/common';
import { BaseAsset, SupportedAsset } from '@rotki/common/lib/data';
import { z } from 'zod';
import { CONFLICT_RESOLUTION } from '@/services/assets/consts';

export interface UnderlyingToken {
  readonly address: string;
  readonly weight: string;
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

export interface HistoricalPrice {
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly timestamp: number;
  readonly price: BigNumber;
}

export interface HistoricalPriceDeletePayload {
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly timestamp: number;
}

export interface HistoricalPricePayload {
  readonly fromAsset: string;
  readonly toAsset: string;
}

export const PriceInformation = z.object({
  usdPrice: NumericString,
  manuallyInput: z.boolean(),
  priceAsset: z.string().nonempty(),
  priceInAsset: NumericString
});

export type PriceInformation = z.infer<typeof PriceInformation>;
export const AssetPrice = PriceInformation.merge(AssetEntry);

export type AssetPrice = z.infer<typeof AssetPrice>;

export const AssetPriceArray = z.array(AssetPrice);

export type AssetPriceArray = z.infer<typeof AssetPriceArray>;
