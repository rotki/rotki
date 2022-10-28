import { Balance, BigNumber, NumericString } from '@rotki/common';
import { forEach } from 'lodash';
import { z } from 'zod';
import { PriceOracle, PriceOracleEnum } from '@/types/price-oracle';
import { MissingPrice } from '@/types/reports';

export const AssetPriceInput = z.tuple([NumericString, z.number()]);
export const AssetPrice = z.object({
  value: NumericString,
  isManualPrice: z.boolean()
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
      mappedAssets[asset] = {
        value: val[0],
        isManualPrice: val[1] === response.oracles.manualcurrent
      };
    });

    return mappedAssets;
  });

export type AssetPriceResponse = z.infer<typeof AssetPriceResponse>;

export type OracleCachePayload = {
  readonly source: PriceOracle;
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly purgeOld: boolean;
};

type TimedPrices = { [timestamp: string]: BigNumber };

type AssetTimedPrices = { [asset: string]: TimedPrices };

export type HistoricPrices = {
  readonly assets: AssetTimedPrices;
  readonly targetAsset: string;
};

export type HistoricPricePayload = {
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly timestamp: number;
};

export interface AssetPriceInfo extends Balance {
  readonly usdPrice: BigNumber;
}

export type EditableMissingPrice = MissingPrice & {
  price: string;
  saved: boolean;
  useRefreshedHistoricalPrice: boolean;
};
