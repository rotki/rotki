import { default as BigNumber } from 'bignumber.js';
import { Balance } from '@/services/types-api';

interface UniswapAssetDetails {
  readonly ethereumAddress: string;
  readonly name: string;
  readonly symbol: string;
}

interface UniswapAsset {
  readonly asset: UniswapAssetDetails | string;
  readonly totalAmount: BigNumber | null;
  readonly usdPrice: BigNumber;
  readonly userBalance: Balance;
}

interface UniswapBalance {
  readonly address: string;
  readonly assets: UniswapAsset[];
  readonly totalSupply: BigNumber | null;
  readonly userBalance: Balance;
}

export interface UniswapBalances {
  readonly [address: string]: UniswapBalance[];
}
