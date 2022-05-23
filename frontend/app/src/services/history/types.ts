import { Balance, NumericString } from '@rotki/common';
import { z, ZodTypeAny } from 'zod';
import { SUPPORTED_TRADE_LOCATIONS } from '@/data/defaults';
import { SUPPORTED_EXCHANGES } from '@/types/exchanges';
import { LedgerActionEnum } from '@/types/ledger-actions';

export const EthTransactionEvent = z.object({
  eventIdentifier: z.string(),
  sequenceIndex: z.number().or(z.string()),
  timestamp: z.number(),
  location: z.string(),
  locationLabel: z.string().nullish(),
  eventType: z.string().nullish(),
  eventSubtype: z.string().nullish(),
  asset: z.string(),
  balance: Balance,
  notes: z.string().nullish(),
  counterparty: z.string().nullish(),
  identifier: z.number().nullish()
});

export type EthTransactionEvent = z.infer<typeof EthTransactionEvent>;

export type NewEthTransactionEvent = Omit<
  EthTransactionEvent,
  'identifier' | 'ignoredInAccounting' | 'customized'
>;

export const EthTransactionEventWithMeta = z.object({
  customized: z.boolean(),
  entry: EthTransactionEvent
});

export type EthTransactionEventWithMeta = z.infer<
  typeof EthTransactionEventWithMeta
>;

const EntryMeta = z.object({
  ignoredInAccounting: z.boolean().nullish(),
  customized: z.boolean().nullish(),
  decodedEvents: z.array(EthTransactionEventWithMeta).nullish()
});

export type EntryMeta = z.infer<typeof EntryMeta>;

export type EntryWithMeta<T> = {
  readonly entry: T;
} & EntryMeta;

// Common wrapper function
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
  fee: NumericString.nullish(),
  feeCurrency: z.string().nullish(),
  link: z.string().nullish(),
  notes: z.string().nullish()
});

export type Trade = z.infer<typeof Trade>;

export const TradeCollectionResponse = getCollectionResponseType(
  getEntryWithMeta(Trade)
);

export type NewTrade = Omit<Trade, 'tradeId' | 'ignoredInAccounting'>;

export type HistoryRequestPayload = {
  readonly limit: number;
  readonly offset: number;
  readonly orderByAttribute?: string;
  readonly ascending: boolean;
  readonly onlyCache?: boolean;
};

export type TradeRequestPayload = {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly baseAsset?: string;
  readonly quoteAsset?: string;
  readonly tradeType?: string;
} & HistoryRequestPayload;

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
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly asset?: string;
  readonly action?: string;
} & HistoryRequestPayload;

// ETH Transactions
export const EthTransaction = z.object({
  txHash: z.string(),
  timestamp: z.number(),
  blockNumber: z.number(),
  fromAddress: z.string(),
  toAddress: z.string().nullish(),
  value: NumericString,
  gas: NumericString,
  gasPrice: NumericString,
  gasUsed: NumericString,
  inputData: z.string(),
  nonce: z.number()
});

export type EthTransaction = z.infer<typeof EthTransaction>;

export const EthTransactionCollectionResponse = getCollectionResponseType(
  getEntryWithMeta(EthTransaction)
);

export type TransactionRequestPayload = {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly address?: string;
  readonly asset?: string;
  readonly protocols?: string | string[];
} & HistoryRequestPayload;

export type TransactionEventRequestPayload = {
  readonly txHashes?: string[] | null;
  readonly ignoreCache: boolean;
};

// Ledger Actions
export const LedgerAction = z.object({
  identifier: z.number(),
  timestamp: z.number(),
  actionType: LedgerActionEnum,
  location: TradeLocation,
  amount: NumericString,
  asset: z.string(),
  rate: NumericString.nullish(),
  rateAsset: z.string().nullish(),
  link: z.string().nullish(),
  notes: z.string().nullish()
});

export type LedgerAction = z.infer<typeof LedgerAction>;

export const LedgerActionCollectionResponse = getCollectionResponseType(
  getEntryWithMeta(LedgerAction)
);

export type LedgerActionRequestPayload = {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly asset?: string;
  readonly action?: string;
} & HistoryRequestPayload;

export type NewLedgerAction = Omit<LedgerAction, 'identifier'>;
