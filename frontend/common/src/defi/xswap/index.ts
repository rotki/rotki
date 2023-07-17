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

const ApiXswapPoolDetails = z.object({
  poolAddress: z.string(),
  profitLoss0: NumericString,
  profitLoss1: NumericString,
  token0: z.string(),
  token1: z.string(),
  usdProfitLoss: NumericString
});

const XswapPoolDetails = ApiXswapPoolDetails.extend({ address: z.string() });

export type XswapPoolDetails = z.infer<typeof XswapPoolDetails>;

export const XswapPool = z.object({
  address: z.string(),
  assets: z.array(z.string())
});

export type XswapPool = z.infer<typeof XswapPool>;

export const XswapEvents = z
  .record(z.array(ApiXswapPoolDetails))
  .transform(data => {
    const transformed: Record<string, XswapPoolDetails[]> = {};
    // when parsed, data will be a record of ApiXswapPoolDetails[]
    // we transform it to a record of XswapPoolDetails[]
    Object.keys(data).forEach((address: string) => {
      transformed[address] = data[address].map(balance => ({
        ...balance,
        address
      }));
    });
    return transformed;
  });

export type XswapEvents = z.infer<typeof XswapEvents>;

export type XswapPoolProfit = Omit<XswapPoolDetails, 'address'>;
