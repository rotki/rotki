import { AssetEntry, NumericString } from '@rotki/common';
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

export interface AssetPair {
  readonly fromAsset: string;
  readonly toAsset: string;
}

export const AssetPair = z.object({
  fromAsset: z.string(),
  toAsset: z.string()
});

export const ManualPrice = AssetPair.extend({
  price: NumericString
});

export type ManualPrice = z.infer<typeof ManualPrice>;

export const ManualPrices = z.array(ManualPrice);
export type ManualPrices = z.infer<typeof ManualPrices>;

export const HistoricalPrice = ManualPrice.extend({
  timestamp: z.number()
});
export type HistoricalPrice = z.infer<typeof HistoricalPrice>;

export const HistoricalPrices = z.array(HistoricalPrice);
export type HistoricalPrices = z.infer<typeof HistoricalPrices>;

export const ManualPriceFormPayload = AssetPair.extend({
  price: z.string()
});

export type ManualPriceFormPayload = z.infer<typeof ManualPriceFormPayload>;

export const HistoricalPriceFormPayload = ManualPriceFormPayload.extend({
  timestamp: z.number()
});

export type HistoricalPriceFormPayload = z.infer<
  typeof HistoricalPriceFormPayload
>;

export const HistoricalPriceDeletePayload = AssetPair.extend({
  timestamp: z.number()
});

export type HistoricalPriceDeletePayload = z.infer<
  typeof HistoricalPriceDeletePayload
>;

export interface ManualPricePayload {
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
