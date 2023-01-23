import { Balance, NumericString } from '@rotki/common';
import { z } from 'zod';
import { type PaginationRequestPayload } from '@/types/common';
import { EntryMeta } from '@/types/history/meta';

const LiquityStakingEventExtraData = z.object({
  asset: z.string(),
  stakedAmount: NumericString
});

export const EthTransactionEventDetail = z
  .object({
    liquityStaking: LiquityStakingEventExtraData
  })
  .nullish();

export type EthTransactionEventDetail = z.infer<
  typeof EthTransactionEventDetail
>;

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
  entry: EthTransactionEvent,
  hasDetails: z.boolean()
});
export type EthTransactionEventWithMeta = z.infer<
  typeof EthTransactionEventWithMeta
>;
// ETH Transactions
export const EthTransaction = z.object({
  txHash: z.string(),
  timestamp: z.number(),
  blockNumber: z.number(),
  evmChain: z.string(),
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

export interface TransactionRequestPayload
  extends PaginationRequestPayload<EthTransaction> {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly accounts?: EvmChainAddress[] | null;
  readonly asset?: string;
  readonly protocols?: string | string[];
  readonly eventTypes?: string | string[];
  readonly evmChain?: string;
}

export interface TransactionHashAndEvmChainPayload {
  readonly txHashes?: string[] | null;
  readonly evmChain: string;
}

export interface AddressesAndEvmChainPayload {
  readonly addresses?: string[] | null;
  readonly evmChain: string;
}

export const EvmChainAddress = z.object({
  address: z.string(),
  evmChain: z.string()
});

export type EvmChainAddress = z.infer<typeof EvmChainAddress>;

export interface TransactionEventRequestPayload {
  readonly data: TransactionHashAndEvmChainPayload[];
  readonly ignoreCache: boolean;
}

export const TxEntryMeta = EntryMeta.merge(
  z.object({
    decodedEvents: z.array(EthTransactionEventWithMeta).nullish()
  })
);
export type TxEntryMeta = z.infer<typeof TxEntryMeta>;

export const TxEventEntryMeta = EntryMeta.merge(
  z.object({
    customized: z.boolean(),
    hasDetails: z.boolean()
  })
);

export type TxEventEntryMeta = z.infer<typeof TxEventEntryMeta>;

export const EthTransactionCollectionResponse = z.object({
  entries: z.array(
    z
      .object({
        entry: EthTransaction
      })
      .merge(TxEntryMeta)
  ),
  entriesFound: z.number(),
  entriesLimit: z.number().default(-1),
  entriesTotal: z.number(),
  totalUsdValue: NumericString.nullish()
});

export interface EthTransactionEntry extends EthTransaction, TxEntryMeta {}

export interface EthTransactionEventEntry
  extends EthTransactionEvent,
    TxEventEntryMeta {}
