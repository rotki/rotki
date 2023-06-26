import { z } from 'zod';
import { Balance, NumericString } from '../../index';

export const XswapAsset = z.object({
  asset: z.string(),
  totalAmount: NumericString.nullish(),
  usdPrice: NumericString,
  userBalance: Balance
});
export type XswapAsset = z.infer<typeof XswapAsset>;

export const XswapBalance = z.object({
  account: z.string().nullish(),
  assets: z.array(XswapAsset),
  address: z.string(),
  totalSupply: NumericString.nullish(),
  nftId: z.string().nullish(),
  priceRange: z.array(NumericString).nullish(),
  userBalance: Balance
});
export type XswapBalance = z.infer<typeof XswapBalance>;

export const XswapBalances = z.record(z.array(XswapBalance));
export type XswapBalances = z.infer<typeof XswapBalances>;

const XswapPoolDetails = z.object({
  address: z.string(),
  poolAddress: z.string(),
  profitLoss0: NumericString,
  profitLoss1: NumericString,
  token0: z.string(),
  token1: z.string(),
  usdProfitLoss: NumericString
});

export type XswapPoolDetails = z.infer<typeof XswapPoolDetails>;

export const XswapPool = z.object({
  address: z.string(),
  assets: z.array(z.string())
});

export type XswapPool = z.infer<typeof XswapPool>;

export const XswapEvents = z.record(z.array(XswapPoolDetails));

export type XswapEvents = z.infer<typeof XswapEvents>;

export type XswapPoolProfit = Omit<XswapPoolDetails, 'address'>;
