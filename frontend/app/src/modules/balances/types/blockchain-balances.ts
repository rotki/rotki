import { Balance, NumericString } from '@rotki/common';
import { z } from 'zod';

const ClaimRequestSchema = z.object({
  amount: NumericString,
  availableAt: z.number().optional(),
  finalized: z.boolean(),
  id: z.string().optional(),
  requestedAt: z.number().optional(),
});

const ProtocolBalances = z.record(z.string(), Balance.extend({
  awaitingClaim: NumericString.optional(),
  claims: z.array(ClaimRequestSchema).optional(),
}));

export type ProtocolBalances = z.infer<typeof ProtocolBalances>;

const AssetBalancesSchema = z.record(z.string(), Balance);

const AssetProtocolBalancesSchema = z.record(z.string(), ProtocolBalances);

export type AssetProtocolBalances = z.infer<typeof AssetProtocolBalancesSchema>;

const BlockchainTotals = z.object({
  assets: AssetProtocolBalancesSchema,
  liabilities: AssetProtocolBalancesSchema,
});

export type BlockchainTotals = z.infer<typeof BlockchainTotals>;

const XpubBalance = z.object({
  addresses: z.record(z.string(), Balance),
  derivationPath: z.string().nullable(),
  xpub: z.string(),
});

const BtcBalances = z.object({
  standalone: AssetBalancesSchema.optional(),
  xpubs: z.array(XpubBalance).optional(),
});

export type BtcBalances = z.infer<typeof BtcBalances>;

const EthBalance = z.object({
  assets: AssetProtocolBalancesSchema,
  liabilities: AssetProtocolBalancesSchema,
});

export type EthBalance = z.infer<typeof EthBalance>;

const BlockchainAssetBalances = z.record(z.string(), EthBalance);

export type BlockchainAssetBalances = z.infer<typeof BlockchainAssetBalances>;

const PerAccountBalances = z.record(z.string(), BlockchainAssetBalances.or(BtcBalances));

export const BlockchainBalances = z.object({
  lastRefreshTs: z.record(z.string(), z.number()).optional(),
  perAccount: PerAccountBalances,
  totals: BlockchainTotals,
});

export type BlockchainBalances = z.infer<typeof BlockchainBalances>;

export interface BlockchainBalancePayload {
  readonly addresses?: string[];
  readonly blockchain?: string | string[];
  readonly isXpub?: boolean;
}

export interface FetchBlockchainBalancePayload {
  readonly addresses?: string[];
  readonly isXpub?: boolean;
  readonly blockchain: string;
}
