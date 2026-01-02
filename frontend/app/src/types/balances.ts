import { Balance, type BigNumber } from '@rotki/common';
import { z } from 'zod/v4';

export interface Eth2Validator {
  readonly validatorIndex?: string;
  readonly publicKey?: string;
  readonly ownershipPercentage?: string;
}

export interface LocationBalance {
  readonly location: string;
  readonly value: BigNumber;
}

export type BalanceByLocation = Record<string, BigNumber>;

export const AssetBalances = z.record(z.string(), Balance);

export type AssetBalances = z.infer<typeof AssetBalances>;

export const AccountAssetBalances = z.record(z.string(), AssetBalances);

export type AccountAssetBalances = z.infer<typeof AccountAssetBalances>;

export enum BalanceType {
  ASSET = 'asset',
  LIABILITY = 'liability',
}

const EvmTokens = z.object({
  lastUpdateTimestamp: z.number().nullish(),
  tokens: z.array(z.string()).nullish(),
});

export const EvmTokensRecord = z.record(z.string(), EvmTokens);

export type EvmTokensRecord = z.infer<typeof EvmTokensRecord>;

export interface EthDetectedTokensInfo {
  tokens: string[];
  total: number;
  timestamp: number | null;
}

export const HistoricalAssetBalance = z.object({
  amount: z.string(),
  price: z.string(),
});

export type HistoricalAssetBalance = z.infer<typeof HistoricalAssetBalance>;

export const HistoricalBalancesAllAssetsResponse = z.object({
  processingRequired: z.literal(false),
  entries: z.record(z.string(), HistoricalAssetBalance),
});

export type HistoricalBalancesAllAssetsResponse = z.infer<typeof HistoricalBalancesAllAssetsResponse>;

export const HistoricalBalancesSingleAssetResponse = z.object({
  processingRequired: z.literal(false),
  entries: HistoricalAssetBalance,
});

export type HistoricalBalancesSingleAssetResponse = z.infer<typeof HistoricalBalancesSingleAssetResponse>;

export const HistoricalBalancesProcessingRequiredResponse = z.object({
  processingRequired: z.literal(true),
});

export type HistoricalBalancesProcessingRequiredResponse = z.infer<typeof HistoricalBalancesProcessingRequiredResponse>;

export interface HistoricalBalancesPayload {
  timestamp: number;
  asset?: string;
}
