import { BigNumber } from "bignumber.js";

interface DexSwap {
  readonly amount0In: BigNumber;
  readonly amount0Out: BigNumber;
  readonly amount1In: BigNumber;
  readonly amount1Out: BigNumber;
  readonly fromAddress: string;
  readonly location: "uniswap";
  readonly logIndex: number;
  readonly toAddress: string;
  readonly token0: string;
  readonly token1: string;
  readonly txHash: string;
}

export interface DexTrade {
  readonly address: string;
  readonly amount: BigNumber;
  readonly baseAsset: string;
  readonly fee: BigNumber;
  readonly feeCurrency: string;
  readonly location: "uniswap" | "balancer";
  readonly quoteAsset: string;
  readonly rate: BigNumber;
  readonly swaps: DexSwap[];
  readonly timestamp: number;
  readonly tradeId: string;
  readonly tradeType: 'buy' | 'sell';
  readonly txHash: string;
}