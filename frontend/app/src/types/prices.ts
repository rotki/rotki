import { type PriceOracle, PriceOracleEnum } from '@/types/settings/price-oracle';
import { AssetEntry, type Balance, type BigNumber, NumericString } from '@rotki/common';
import { forEach } from 'es-toolkit/compat';
import { z } from 'zod';

export const AssetPriceInput = z.tuple([NumericString, z.number()]);

export const AssetPrice = z.object({
  isManualPrice: z.boolean(),
  oracle: z.string(),
  usdPrice: NumericString.nullish(),
  value: NumericString,
});

export type AssetPrice = z.infer<typeof AssetPrice>;

export const AssetPrices = z.record(AssetPrice);

export type AssetPrices = z.infer<typeof AssetPrices>;

export const AssetPriceResponse = z.object({
  assets: z.record(AssetPriceInput),
  oracles: z.record(PriceOracleEnum, z.number()),
  targetAsset: z.string(),
}).transform((response) => {
  const mappedAssets: AssetPrices = {};
  const assets = response.assets;

  forEach(assets, (val, asset) => {
    const [value, oracle] = val;
    const oracleKey = Object.entries(response.oracles).find(([_, value]) => value === oracle)?.[0] ?? '';

    mappedAssets[asset] = {
      isManualPrice: oracle === response.oracles.manualcurrent,
      oracle: oracleKey,
      value,
    };
  });

  return mappedAssets;
});

export type AssetPriceResponse = z.infer<typeof AssetPriceResponse>;

export const AssetPair = z.object({
  fromAsset: z.string(),
  toAsset: z.string(),
});

export type AssetPair = z.infer<typeof AssetPair>;

export interface OracleCachePayload extends AssetPair {
  readonly source: PriceOracle;
  readonly purgeOld: boolean;
}

export interface OracleCacheMeta extends AssetPair {
  readonly fromTimestamp: string;
  readonly toTimestamp: string;
}

const TimedPrices = z.record(NumericString);
const AssetTimedPrices = z.record(TimedPrices);

export const HistoricPrices = z.object({
  assets: AssetTimedPrices,
  targetAsset: z.string(),
});

export type HistoricPrices = z.infer<typeof HistoricPrices>;

export interface HistoricPricePayload extends AssetPair {
  readonly timestamp: number;
}

export interface HistoricPricesPayload {
  readonly assetsTimestamp: string[][];
  readonly targetAsset: string;
  readonly onlyCachePeriod?: number;
}

export interface AssetPriceInfo extends Balance {
  readonly usdPrice: BigNumber;
}

export const ManualPrice = AssetPair.extend({
  price: NumericString,
});

export type ManualPrice = z.infer<typeof ManualPrice>;

export type ManualPriceWithUsd = ManualPrice & {
  id: number;
  usdPrice: BigNumber;
};

export const ManualPrices = z.array(ManualPrice);

export type ManualPrices = z.infer<typeof ManualPrices>;

export const HistoricalPrice = ManualPrice.extend({
  timestamp: z.number(),
});

export type HistoricalPrice = z.infer<typeof HistoricalPrice>;

export const HistoricalPrices = z.array(HistoricalPrice);

export type HistoricalPrices = z.infer<typeof HistoricalPrices>;

export const ManualPriceFormPayload = AssetPair.extend({
  price: z.string(),
});

export type ManualPriceFormPayload = z.infer<typeof ManualPriceFormPayload>;

export const HistoricalPriceFormPayload = ManualPriceFormPayload.extend({
  timestamp: z.number(),
});

export type HistoricalPriceFormPayload = z.infer<typeof HistoricalPriceFormPayload>;

export const HistoricalPriceDeletePayload = AssetPair.extend({
  timestamp: z.number(),
});

export type HistoricalPriceDeletePayload = z.infer<typeof HistoricalPriceDeletePayload>;

export interface ManualPricePayload {
  readonly fromAsset: string | null;
  readonly toAsset: string | null;
}

export const PriceInformation = z.object({
  manuallyInput: z.boolean(),
  priceAsset: z.string().min(1),
  priceInAsset: NumericString,
  usdPrice: NumericString,
});

export type PriceInformation = z.infer<typeof PriceInformation>;

export const NftPrice = PriceInformation.merge(AssetEntry);

export type NftPrice = z.infer<typeof NftPrice>;

export const NftPriceArray = z.array(NftPrice);

export type NftPriceArray = z.infer<typeof NftPriceArray>;
