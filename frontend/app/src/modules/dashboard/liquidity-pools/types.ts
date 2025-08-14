import { Balance, type BigNumber, NumericString } from '@rotki/common';
import z from 'zod/v4';

const PoolAsset = z.object({
  asset: z.string(),
  totalAmount: NumericString.nullish(),
  usdPrice: NumericString,
  userBalance: Balance,
});

export type PoolAsset = z.infer<typeof PoolAsset>;

const PoolBalance = z.object({
  account: z.string().nullish(),
  address: z.string(),
  assets: z.array(PoolAsset),
  nftId: z.string().nullish(),
  priceRange: z.array(NumericString).nullish(),
  totalSupply: NumericString.nullish(),
  userBalance: Balance,
});

export type PoolBalance = z.infer<typeof PoolBalance>;

export const PoolBalances = z.record(z.string(), z.array(PoolBalance));

export type PoolBalances = z.infer<typeof PoolBalances>;

export enum PoolType {
  UNISWAP_V2 = 'uniswap_v2',
  SUSHISWAP = 'sushiswap',
}

export interface PoolLiquidityBalance {
  id: number;
  usdValue: BigNumber;
  premiumOnly: boolean;
  asset: string;
  type: PoolType;
  assets: PoolBalance['assets'];
}
