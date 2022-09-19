import { Balance, BigNumber } from '@rotki/common';
import { PriceOracle } from '@/types/price-oracle';

export type AssetPrices = {
  [asset: string]: BigNumber;
};

export type AssetPriceResponse = {
  readonly assets: AssetPrices;
  readonly targetAsset: string;
};

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
