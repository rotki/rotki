import { default as BigNumber } from "bignumber.js";
import { z } from 'zod';
import { Balance, NumericString } from "../../index";

export const XswapAsset = z.object({
  asset: z.string(),
  totalAmount: NumericString.nullish(),
  usdPrice: NumericString,
  userBalance: Balance,
})
export type XswapAsset = z.infer<typeof XswapAsset>;

export const XswapBalance = z.object({
  account: z.string().nullish(),
  assets: z.array(XswapAsset),
  address: z.string(),
  totalSupply: NumericString.nullish(),
  nftId: z.string().nullish(),
  priceRange: z.array(NumericString).nullish(),
  userBalance: Balance,
})
export type XswapBalance = z.infer<typeof XswapBalance>;

export const XswapBalances = z.record(z.array(XswapBalance));
export type XswapBalances = z.infer<typeof XswapBalances>;

export enum XswapEventType {
  MINT = 'mint',
  BURN = 'burn',
}

interface XswapEvent {
  readonly amount0: BigNumber;
  readonly amount1: BigNumber;
  readonly eventType: XswapEventType;
  readonly logIndex: number;
  readonly lpAmount: BigNumber;
  readonly timestamp: number;
  readonly txHash: string;
  readonly usdPrice: BigNumber;
}

interface XswapPoolDetails {
  readonly address: string;
  readonly events: XswapEvent[];
  readonly poolAddress: string;
  readonly profitLoss0: BigNumber;
  readonly profitLoss1: BigNumber;
  readonly token0: string;
  readonly token1: string;
  readonly usdProfitLoss: BigNumber;
}

export const XswapPool = z.object({
  address: z.string(),
  assets: z.array(z.string())
})

export type XswapPool = z.infer<typeof XswapPool>;

export interface XswapEvents {
  readonly [address: string]: XswapPoolDetails[];
}

export type XswapPoolProfit = Omit<XswapPoolDetails, "events" | "address">

export interface XswapEventDetails
  extends XswapEvent,
    Pick<XswapPoolDetails, "address" | "poolAddress" | "token0" | "token1"> {
}
