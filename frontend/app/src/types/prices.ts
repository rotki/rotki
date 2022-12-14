import { type Balance, type BigNumber, NumericString } from '@rotki/common';
import { forEach } from 'lodash';
import { z } from 'zod';
import { type PriceOracle, PriceOracleEnum } from '@/types/price-oracle';
import { type MissingPrice } from '@/types/reports';

export const AssetPriceInput = z.tuple([
  NumericString,
  z.number(),
  z.boolean()
]);

export const AssetPrice = z.object({
  value: NumericString,
  usdPrice: NumericString.nullish(),
  isManualPrice: z.boolean(),
  isCurrentCurrency: z.boolean()
});

export const AssetPrices = z.record(AssetPrice);
export type AssetPrices = z.infer<typeof AssetPrices>;

export const AssetPriceResponse = z
  .object({
    assets: z.record(AssetPriceInput),
    targetAsset: z.string(),
    oracles: z.record(PriceOracleEnum, z.number())
  })
  .transform(response => {
    const mappedAssets: AssetPrices = {};
    const assets = response.assets;
    forEach(assets, (val, asset) => {
      const [value, oracle, isCurrentCurrency] = val;
      mappedAssets[asset] = {
        value,
        isManualPrice: oracle === response.oracles.manualcurrent,
        isCurrentCurrency
      };
    });

    return mappedAssets;
  });

export type AssetPriceResponse = z.infer<typeof AssetPriceResponse>;

export interface OracleCachePayload {
  readonly source: PriceOracle;
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly purgeOld: boolean;
}

const TimedPrices = z.record(NumericString);
const AssetTimedPrices = z.record(TimedPrices);

export const HistoricPrices = z.object({
  assets: AssetTimedPrices,
  targetAsset: z.string()
});
export type HistoricPrices = z.infer<typeof HistoricPrices>;

export interface HistoricPricePayload {
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly timestamp: number;
}

export interface AssetPriceInfo extends Balance {
  readonly usdPrice: BigNumber;
}

export interface EditableMissingPrice extends MissingPrice {
  price: string;
  saved: boolean;
  useRefreshedHistoricalPrice: boolean;
}
