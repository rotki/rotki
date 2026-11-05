import type { FormatOptions } from '@/modules/assets/amount-display/types';
import type { TableColumn } from '@/modules/core/table/table-column';
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

export const ExchangeBalancesResponse = z.object({
  failedAccounts: z.record(z.string(), z.record(z.string(), z.string())).optional(),
  totals: z.record(z.string(), AssetBalances),
});

export type ExchangeBalancesResponse = z.infer<typeof ExchangeBalancesResponse>;

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
 * How an asset row expands into its breakdown.
 *
 * @remarks
 * These four travel together from `AssetBalances` through `AssetRowDetails` and back, so they are
 * one prop rather than four forwarded individually. Declared here rather than in either SFC, because
 * those two import each other.
 */
export interface AssetBreakdownOptions {
  scope?: AssetBreakdownScope;
  isLiability?: boolean;
  /** Include non-blockchain locations in an EVM native token's breakdown. */
  all?: boolean;
  /** Suppress the native-token breakdown entirely. */
  hide?: boolean;
}

/** How an `AssetBalances` table lays itself out and shows its cells, as one prop. */
export interface AssetBalancesDisplay {
  /** Keep the header in view while the page scrolls. */
  stickyHeader?: boolean;
  /** Optional columns to add, such as the share of the net value. */
  visibleColumns?: TableColumn[];
  /** Add a column naming where each asset is held. */
  showPerProtocol?: boolean;
  /** The format of an asset's amount, for a source whose amounts have a known precision such as a bank's. */
  amountFormat?: (asset: string) => FormatOptions;
}
