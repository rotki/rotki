import type { BigNumber } from '@rotki/common';

export interface TradableAssetWithoutValue {
  asset: string;
  chain: string;
  amount: BigNumber;
}

export interface TradableAsset extends TradableAssetWithoutValue {
  fiatValue?: BigNumber;
  price?: BigNumber;
}
