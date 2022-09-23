import { AssetEntry, NumericString, BigNumber } from '@rotki/common';
import { z } from 'zod';
import { CONFLICT_RESOLUTION } from '@/services/assets/consts';

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

export interface HistoricalPrice {
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly timestamp: number;
  readonly price: BigNumber;
}

export interface HistoricalPriceFormPayload {
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly timestamp: number;
  readonly price: string;
}

export interface HistoricalPriceDeletePayload {
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly timestamp: number;
}

export interface HistoricalPricePayload {
  readonly fromAsset: string | null;
  readonly toAsset: string | null;
}

export const PriceInformation = z.object({
  usdPrice: NumericString,
  manuallyInput: z.boolean(),
  priceAsset: z.string().nonempty(),
  priceInAsset: NumericString
});

export type PriceInformation = z.infer<typeof PriceInformation>;

export const AssetPrice = PriceInformation.merge(AssetEntry);

export const AssetPriceArray = z.array(AssetPrice);

export type AssetPriceArray = z.infer<typeof AssetPriceArray>;
