import { NumericString } from '@rotki/common';
import { z, ZodTypeAny } from 'zod';
import { SUPPORTED_TRADE_LOCATIONS } from '@/data/defaults';
import { SUPPORTED_EXCHANGES } from '@/types/exchanges';
import { LedgerActionEnum } from '@/types/ledger-actions';

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
export const TradeType = z.enum([
  'buy',
  'sell',
  'settlement buy',
  'settlement sell'
]);
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
export const MovementCategory = z.enum(['deposit', 'withdrawal']);
export type MovementCategory = z.infer<typeof MovementCategory>;

export const AssetMovement = z.object({
  identifier: z.string(),
  location: TradeLocation,
  category: MovementCategory,
  address: z.string().nullable(),
  transactionId: z.string().nullable(),
  timestamp: z.number(),
  asset: z.string(),
  amount: NumericString,
  feeAsset: z.string(),
  fee: NumericString,
  link: z.string()
});

export type AssetMovement = z.infer<typeof AssetMovement>;

export const AssetMovementCollectionResponse = getCollectionResponseType(
  getEntryWithMeta(AssetMovement)
);

export type AssetMovementRequestPayload = {
  readonly limit: number;
  readonly offset: number;
  readonly orderByAttribute?: string;
  readonly ascending: boolean;
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly asset?: string;
  readonly action?: string;
  readonly onlyCache?: boolean;
};

// ETH Transactions
export const EthTransaction = z.object({
  txHash: z.string(),
  timestamp: z.number(),
  blockNumber: z.number(),
  fromAddress: z.string(),
  toAddress: z.string().nullable().optional(),
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
export const LedgerAction = z.object({
  identifier: z.number(),
  timestamp: z.number(),
  actionType: LedgerActionEnum,
  location: TradeLocation,
  amount: NumericString,
  asset: z.string(),
  rate: NumericString.nullable().optional(),
  rateAsset: z.string().nullable().optional(),
  link: z.string().nullable().optional(),
  notes: z.string().nullable().optional()
});

export type LedgerAction = z.infer<typeof LedgerAction>;

export const LedgerActionCollectionResponse = getCollectionResponseType(
  getEntryWithMeta(LedgerAction)
);

export type LedgerActionRequestPayload = {
  readonly limit: number;
  readonly offset: number;
  readonly orderByAttribute?: string;
  readonly ascending: boolean;
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly asset?: string;
  readonly action?: string;
  readonly onlyCache?: boolean;
};

export type NewLedgerAction = Omit<LedgerAction, 'identifier'>;
