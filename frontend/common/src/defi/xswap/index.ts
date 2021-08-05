import { default as BigNumber } from "bignumber.js";
import { Balance } from "../../index";

interface XswapAsset {
  readonly asset: string;
  readonly totalAmount: BigNumber | null;
  readonly usdPrice: BigNumber;
  readonly userBalance: Balance;
}

export interface XswapBalances {
  readonly [address: string]: XswapBalance[];
}

export interface XswapBalance {
  readonly account: string;
  readonly assets: XswapAsset[];
  readonly address: string;
  readonly totalSupply: BigNumber | null;
  readonly userBalance: Balance;
}

enum XswapEventType {
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

export interface XswapPool {
  readonly address: string;
  readonly assets: string[];
}

export interface XswapEvents {
  readonly [address: string]: XswapPoolDetails[];
}

export type XswapPoolProfit = Omit<XswapPoolDetails, "events" | "address">

export interface XswapEventDetails
  extends XswapEvent,
    Pick<XswapPoolDetails, "address" | "poolAddress" | "token0" | "token1"> {
}