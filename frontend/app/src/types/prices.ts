import { AssetEntry, type Balance, type BigNumber, NumericString } from '@rotki/common';
import { forEach } from 'es-toolkit/compat';
import { z } from 'zod/v4';
import { PriceOracle, PriceOracleEnum } from '@/types/settings/price-oracle';

const AssetPriceInput = z.tuple([NumericString, z.number()]);

export const AssetPrice = z.object({
  isManualPrice: z.boolean(),
  oracle: z.string(),
  usdPrice: NumericString.nullish(),
  value: NumericString,
});

export type AssetPrice = z.infer<typeof AssetPrice>;

export const AssetPrices = z.record(z.string(), AssetPrice);

export type AssetPrices = z.infer<typeof AssetPrices>;

export const AssetPriceResponse = z.object({
  assets: z.record(z.string(), AssetPriceInput),
  oracles: z.partialRecord(PriceOracleEnum, z.number()),
  targetAsset: z.string(),
}).transform((response) => {
  const mappedAssets: AssetPrices = {};
  const assets = response.assets;

  forEach(assets, (val, asset) => {
    const [value, oracle] = val;
    const oracleKey = Object.entries(response.oracles).find(([_, value]) => value === oracle)?.[0] ?? '';

    mappedAssets[asset] = {
      isManualPrice: oracle === response.oracles[PriceOracle.MANUALCURRENT],
      oracle: oracleKey,
      value,
    };
  });

  return mappedAssets;
});

export type AssetPriceResponse = z.infer<typeof AssetPriceResponse>;

const AssetPair = z.object({
  fromAsset: z.string(),
  toAsset: z.string(),
});

type AssetPair = z.infer<typeof AssetPair>;

export interface OracleCachePayload extends AssetPair {
  readonly source: PriceOracle;
  readonly purgeOld: boolean;
}

export interface OracleCacheMeta extends AssetPair {
  readonly fromTimestamp: string;
  readonly toTimestamp: string;
}

const TimedPrices = z.record(z.string(), NumericString);
const AssetTimedPrices = z.record(z.string(), TimedPrices);

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

export const ManualPrice = z.object({
  ...AssetPair.shape,
  price: NumericString,
});

export type ManualPrice = z.infer<typeof ManualPrice>;

export type ManualPriceWithUsd = ManualPrice & {
  id: number;
  usdPrice: BigNumber;
};

export const ManualPrices = z.array(ManualPrice);

export type ManualPrices = z.infer<typeof ManualPrices>;

export const HistoricalPrice = z.object({
  ...ManualPrice.shape,
  timestamp: z.number(),
});

export type HistoricalPrice = z.infer<typeof HistoricalPrice>;

export const HistoricalPrices = z.array(HistoricalPrice);

export type HistoricalPrices = z.infer<typeof HistoricalPrices>;

export const ManualPriceFormPayload = z.object({
  ...AssetPair.shape,
  price: z.string(),
});

export type ManualPriceFormPayload = z.infer<typeof ManualPriceFormPayload>;

export const HistoricalPriceFormPayload = z.object({
  ...ManualPriceFormPayload.shape,
  timestamp: z.number(),
});

export type HistoricalPriceFormPayload = z.infer<typeof HistoricalPriceFormPayload>;

export const HistoricalPriceDeletePayload = z.object({
  ...AssetPair.shape,
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
  price: NumericString,
});

export type PriceInformation = z.infer<typeof PriceInformation>;

export const NftPrice = z.object({
  ...PriceInformation.shape,
  ...AssetEntry.shape,
});

export type NftPrice = z.infer<typeof NftPrice>;

export const NftPriceArray = z.array(NftPrice);

export type NftPriceArray = z.infer<typeof NftPriceArray>;
