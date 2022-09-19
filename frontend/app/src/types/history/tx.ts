import { Balance, NumericString } from '@rotki/common';
import { z } from 'zod';
import { getCollectionResponseType } from '@/types/collection';
import { HistoryRequestPayload } from '@/types/history/index';
import { EntryMeta, getEntryWithMeta } from '@/types/history/meta';

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
export type TransactionRequestPayload = {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly address?: string;
  readonly asset?: string;
  readonly protocols?: string | string[];
} & HistoryRequestPayload<EthTransaction>;
export type TransactionEventRequestPayload = {
  readonly txHashes?: string[] | null;
  readonly ignoreCache: boolean;
};

export const TxEntryMeta = EntryMeta.merge(
  z.object({
    decodedEvents: z.array(EthTransactionEventWithMeta).nullish()
  })
);

export type TxEntryMeta = z.infer<typeof TxEntryMeta>;

export const EthTransactionCollectionResponse = getCollectionResponseType(
  getEntryWithMeta(EthTransaction, TxEntryMeta)
);
