import { z } from 'zod';
import { AssetBalance, Balance } from '../balances';
import { NumericString } from '../numbers';

const TimedEntry = z.object({ time: z.number().positive() });

const TimedBalance = Balance.merge(TimedEntry);

export type TimedBalance = z.infer<typeof TimedBalance>;

export const TimedBalances = z.array(TimedBalance);

export type TimedBalances = z.infer<typeof TimedBalances>;

export const OwnedAssets = z.array(z.string());

export type OwnedAssets = z.infer<typeof OwnedAssets>;

const LocationDataItem = z.object({
  location: z.string().min(1),
  time: z.number().positive(),
  usdValue: NumericString,
});

export const LocationData = z.array(LocationDataItem);

export type LocationData = z.infer<typeof LocationData>;

const TimedAssetBalance = AssetBalance.merge(TimedEntry);

export const TimedAssetBalances = z.array(TimedAssetBalance);

export type TimedAssetBalances = z.infer<typeof TimedAssetBalances>;

export const NetValue = z.object({
  data: z.array(NumericString),
  times: z.array(z.number()),
});

export type NetValue = z.infer<typeof NetValue>;

export const TimedAssetHistoricalBalances = z.object({
  lastEventIdentifier: z.tuple([z.number(), z.string()]).optional(),
  times: z.array(z.number().positive()),
  values: z.array(NumericString),
});

export type TimedAssetHistoricalBalances = z.infer<typeof TimedAssetHistoricalBalances>;

export const HistoricalAssetPricePayload = z.object({
  asset: z.string(),
  excludeTimestamps: z.array(z.number()).optional(),
  fromTimestamp: z.number(),
  interval: z.number(),
  onlyCachePeriod: z.number().optional(),
  toTimestamp: z.number(),
});

export type HistoricalAssetPricePayload = z.infer<typeof HistoricalAssetPricePayload>;

export const FailedHistoricalAssetPriceResponse = z.object({
  noPricesTimestamps: z.array(z.number()),
  rateLimitedPricesTimestamps: z.array(z.number()),
});

export type FailedHistoricalAssetPriceResponse = z.infer<typeof FailedHistoricalAssetPriceResponse>;

export const HistoricalAssetPriceResponse = FailedHistoricalAssetPriceResponse.extend({
  prices: z.record(NumericString),
});

export type HistoricalAssetPriceResponse = z.infer<typeof HistoricalAssetPriceResponse>;

export const CommonQueryStatusData = z.object({
  processed: z.number(),
  total: z.number(),
});

export type CommonQueryStatusData = z.infer<typeof CommonQueryStatusData>;
