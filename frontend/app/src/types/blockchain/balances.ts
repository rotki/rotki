import { Balance } from '@rotki/common';
import { z } from 'zod';

export const Balances = z.record(Balance);

export type Balances = z.infer<typeof Balances>;

const BlockchainTotals = z.object({
  assets: Balances,
  liabilities: Balances,
});

export type BlockchainTotals = z.infer<typeof BlockchainTotals>;

const XpubBalance = z.object({
  addresses: z.record(Balance),
  derivationPath: z.string().nullable(),
  xpub: z.string(),
});

const BtcBalances = z.object({
  standalone: Balances.optional(),
  xpubs: z.array(XpubBalance).optional(),
});

export type BtcBalances = z.infer<typeof BtcBalances>;

const EthBalance = z.object({
  assets: Balances,
  liabilities: Balances,
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
