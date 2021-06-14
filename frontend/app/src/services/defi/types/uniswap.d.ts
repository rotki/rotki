import { default as BigNumber } from 'bignumber.js';
import { Balance } from '@/services/types-api';

interface UniswapAsset {
  readonly asset: string;
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
