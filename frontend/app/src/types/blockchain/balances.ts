import { Balance } from '@rotki/common';
import { z } from 'zod';

const ProtocolBalances = z.record(Balance);

export type ProtocolBalances = z.infer<typeof ProtocolBalances>;

const AssetBalancesSchema = z.record(Balance);

export type AssetBalances = z.infer<typeof AssetBalancesSchema>;

export const AssetProtocolBalancesSchema = z.record(ProtocolBalances);

export type AssetProtocolBalances = z.infer<typeof AssetProtocolBalancesSchema>;

const BlockchainTotals = z.object({
  assets: AssetProtocolBalancesSchema,
  liabilities: AssetProtocolBalancesSchema,
});

export type BlockchainTotals = z.infer<typeof BlockchainTotals>;

const XpubBalance = z.object({
  addresses: z.record(Balance),
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

const BlockchainAssetBalances = z.record(EthBalance);

export type BlockchainAssetBalances = z.infer<typeof BlockchainAssetBalances>;

const PerAccountBalances = z.record(BlockchainAssetBalances.or(BtcBalances));

export const BlockchainBalances = z.object({
  perAccount: PerAccountBalances,
  totals: BlockchainTotals,
});

export type BlockchainBalances = z.infer<typeof BlockchainBalances>;
