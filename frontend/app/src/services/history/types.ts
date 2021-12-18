import { NumericString, BigNumber } from '@rotki/common';
import { z, ZodTypeAny } from 'zod';
import { SUPPORTED_TRADE_LOCATIONS } from '@/data/defaults';
import { SUPPORTED_EXCHANGES } from '@/types/exchanges';

// Common wrapper function
const EntryMeta = z.object({
  ignoredInAccounting: z.boolean()
});

export type EntryMeta = z.infer<typeof EntryMeta>;

export type EntryWithMeta<T> = {
  readonly entry: T;
} & EntryMeta;

function getEntryWithMeta(obj: ZodTypeAny) {
  return z
    .object({
      entry: obj
    })
    .merge(EntryMeta);
}

function getCollectionResponseType(obj: ZodTypeAny) {
  return z.object({
    entries: z.array(obj),
    entriesFound: z.number(),
    entriesLimit: z.number(),
    entriesTotal: z.number()
  });
}

// Trades
export const TradeType = z.enum(['buy', 'sell']);
export type TradeType = z.infer<typeof TradeType>;

// @ts-ignore
export const TradeLocation = z.enum([
  ...SUPPORTED_EXCHANGES,
  ...SUPPORTED_TRADE_LOCATIONS,
  'gitcoin'
]);

export type TradeLocation = z.infer<typeof TradeLocation>;

export const Trade = z.object({
  tradeId: z.string(),
  timestamp: z.number(),
  location: TradeLocation,
  baseAsset: z.string(),
  quoteAsset: z.string(),
  tradeType: TradeType,
  amount: NumericString,
  rate: NumericString,
  fee: NumericString.nullable().optional(),
  feeCurrency: z.string().nullable().optional(),
  link: z.string().nullable().optional(),
  notes: z.string().nullable().optional()
});

export type Trade = z.infer<typeof Trade>;

export const TradeCollectionResponse = getCollectionResponseType(
  getEntryWithMeta(Trade)
);

export type NewTrade = Omit<Trade, 'tradeId' | 'ignoredInAccounting'>;

export type TradeRequestPayload = {
  readonly limit: number;
  readonly offset: number;
  readonly orderByAttribute?: string;
  readonly ascending: boolean;
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly baseAsset?: string;
  readonly quoteAsset?: string;
  readonly tradeType?: string;
  readonly onlyCache?: boolean;
};

// Asset Movements
type MovementCategory = 'deposit' | 'withdrawal';

export interface AssetMovement {
  readonly identifier: string;
  readonly location: TradeLocation;
  readonly category: MovementCategory;
  readonly address: string;
  readonly transactionId: string;
  readonly timestamp: number;
  readonly asset: string;
  readonly amount: BigNumber;
  readonly feeAsset: string;
  readonly fee: BigNumber;
  readonly link: string;
}

// ETH Transactions
export const EthTransaction = z.object({
  txHash: z.string(),
  timestamp: z.number(),
  blockNumber: z.number(),
  fromAddress: z.string(),
  toAddress: z.string(),
  value: NumericString,
  gas: NumericString,
  gasPrice: NumericString,
  gasUsed: NumericString,
  inputData: z.string(),
  nonce: z.number(),
  identifier: z.string()
});

export type EthTransaction = z.infer<typeof EthTransaction>;

export const EthTransactionCollectionResponse = getCollectionResponseType(
  getEntryWithMeta(EthTransaction)
);

export type TransactionRequestPayload = {
  readonly limit: number;
  readonly offset: number;
  readonly orderByAttribute: keyof EthTransaction;
  readonly ascending: boolean;
  readonly fromTimestamp?: number;
  readonly toTimestamp?: number;
  readonly onlyCache?: boolean;
  readonly address?: string;
};

// Ledger Actions
export interface LedgerActionResult {
  readonly identifier: number;
}
