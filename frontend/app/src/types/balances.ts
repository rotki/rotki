import { Balance, type BigNumber } from '@rotki/common';
import { z } from 'zod/v4';

export interface Eth2Validator {
  readonly validatorIndex?: string;
  readonly publicKey?: string;
  readonly ownershipPercentage?: string;
}

export interface LocationBalance {
  readonly location: string;
  readonly usdValue: BigNumber;
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

export const EvmTokens = z.object({
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
