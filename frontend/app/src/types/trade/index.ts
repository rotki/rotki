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

export interface TransactionParams {
  to: string;
  amount: string;
  assetIdentifier?: string;
  native: boolean;
  chain: string;
}

export interface RecentTransaction {
  hash: string;
  chain: string;
  timestamp: number;
  context: string;
  status: 'pending' | 'completed' | 'failed';
  metadata: any;
  initiatorAddress: string;
}

export interface TransactionError extends Error {
  transaction?: {
    hash: string;
  };
}

export interface GasFeeEstimation {
  gasPrice: bigint;
  formatted: string;
  maxAmount: string;
}
