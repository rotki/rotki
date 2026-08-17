import { Balance, type BigNumber } from '@rotki/common';
import { z } from 'zod';

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

/** Which accounts an asset's balance is broken down over. */
interface AssetBreakdownScope {
  groupId?: string;
  chains?: string[];
}

/**
 * How an asset row expands into its breakdown. These four travel together across the
 * AssetBalances -> AssetRowDetails -> AssetBalances boundary, so they are one prop rather than four
 * forwarded individually. Lives here rather than in either SFC because those two import each other.
 */
export interface AssetBreakdownOptions {
  scope?: AssetBreakdownScope;
  isLiability?: boolean;
  /** Include non-blockchain locations in an EVM native token's breakdown. */
  all?: boolean;
  /** Suppress the native-token breakdown entirely. */
  hide?: boolean;
}
