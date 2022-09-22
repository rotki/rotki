import { Balance } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { z } from 'zod';

export const Balances = z.record(Balance);

export type Balances = z.infer<typeof Balances>;

const BlockchainTotals = z.object({
  assets: Balances,
  liabilities: Balances
});

const XpubBalance = z.object({
  xpub: z.string(),
  derivationPath: z.string().nullable(),
  addresses: z.record(Balance)
});

const BtcBalances = z.object({
  standalone: Balances.optional(),
  xpubs: z.array(XpubBalance).optional()
});

export type BtcBalances = z.infer<typeof BtcBalances>;

const EthBalance = z.object({
  assets: Balances,
  liabilities: Balances
});

const BlockchainAssetBalances = z.record(EthBalance);

export type BlockchainAssetBalances = z.infer<typeof BlockchainAssetBalances>;

const PerAccountBalances = z.object({
  [Blockchain.ETH]: BlockchainAssetBalances.optional(),
  [Blockchain.ETH2]: BlockchainAssetBalances.optional(),
  [Blockchain.BTC]: BtcBalances.optional(),
  [Blockchain.BCH]: BtcBalances.optional(),
  [Blockchain.KSM]: BlockchainAssetBalances.optional(),
  [Blockchain.DOT]: BlockchainAssetBalances.optional(),
  [Blockchain.AVAX]: BlockchainAssetBalances.optional()
});

export const BlockchainBalances = z.object({
  perAccount: PerAccountBalances,
  totals: BlockchainTotals
});

export type BlockchainBalances = z.infer<typeof BlockchainBalances>;
