import type { BigNumber } from '@rotki/common';
import { z } from 'zod';

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

export interface PrepareTransferPayload {
  fromAddress: string;
  toAddress: string;
  amount: string;
}

export interface PrepareERC20TransferPayload extends PrepareTransferPayload {
  token: string;
}

export const PrepareERC20TransferResponse = z.object({
  chainId: z.number(),
  data: z.string(),
  from: z.string(),
  gas: z.number(),
  maxFeePerGas: z.number(),
  maxPriorityFeePerGas: z.number(),
  nonce: z.number(),
  to: z.string(),
  value: z.number().transform(arg => BigInt(arg)),
});

export type PrepareERC20TransferResponse = z.infer<typeof PrepareERC20TransferResponse>;

export interface PrepareNativeTransferPayload extends PrepareTransferPayload {
  chain: string;
}

export const PrepareNativeTransferResponse = z.object({
  from: z.string(),
  maxFeePerGas: z.number().transform(arg => arg.toString()),
  maxPriorityFeePerGas: z.number().transform(arg => arg.toString()),
  nonce: z.number(),
  to: z.string(),
  value: z.number().transform(arg => BigInt(arg)),
});

export type PrepareNativeTransferResponse = z.infer<typeof PrepareNativeTransferResponse>;
