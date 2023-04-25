import { Balance, NumericString } from '@rotki/common';
import { z } from 'zod';
import { type PaginationRequestPayload } from '@/types/common';
import { EntryMeta } from '@/types/history/meta';
import { CollectionCommonFields } from '@/types/collection';

const LiquityStakingEventExtraData = z.object({
  asset: z.string(),
  stakedAmount: NumericString
});

// ETH Transactions
export const EvmTransaction = z.object({
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
export type EvmTransaction = z.infer<typeof EvmTransaction>;

export interface TransactionRequestPayload
  extends PaginationRequestPayload<{ timestamp: number }> {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly accounts?: EvmChainAddress[] | null;
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

export interface EvmChainAndTxHash {
  readonly evmChain: string;
  readonly txHash: string;
}

export interface AddTransactionHashPayload extends EvmChainAndTxHash {
  readonly associatedAddress: string;
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

export const HistoryEventDetail = z
  .object({
    liquityStaking: LiquityStakingEventExtraData
  })
  .nullish();

export type HistoryEventDetail = z.infer<typeof HistoryEventDetail>;

export const HistoryEvent = z.object({
  identifier: z.number().nullish(),
  eventIdentifier: z.string(),
  sequenceIndex: z.number().or(z.string()),
  timestamp: z.number(),
  location: z.string(),
  asset: z.string(),
  balance: Balance,
  eventType: z.string().nullish(),
  eventSubtype: z.string().nullish(),
  locationLabel: z.string().nullish(),
  notes: z.string().nullish(),
  counterparty: z.string().nullish(),
  product: z.string().nullish(),
  address: z.string().nullish(),
  isExit: z.boolean().optional(),
  validatorIndex: z.number().optional()
});
export type HistoryEvent = z.infer<typeof HistoryEvent>;

export interface HistoryEventRequestPayload
  extends PaginationRequestPayload<{ timestamp: number }> {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly groupByEventIds: boolean;
  readonly eventIdentifiers?: string | string[];
  readonly eventTypes?: string | string[];
  readonly eventSubtypes?: string | string[];
  readonly locationLabels?: string | string[];
  readonly asset?: string;
  readonly counterparties?: string | string[];
  readonly location?: string | string[];
  readonly product?: string | string[];
}

export type NewHistoryEvent = Omit<
  HistoryEvent,
  'identifier' | 'ignoredInAccounting' | 'customized'
>;

export const HistoryEventMeta = EntryMeta.merge(
  z.object({
    customized: z.boolean(),
    hasDetails: z.boolean(),
    groupedEventsNum: z.number().nullish()
  })
);

export type HistoryEventMeta = z.infer<typeof HistoryEventMeta>;

const HistoryEventEntryWithMeta = z
  .object({
    entry: HistoryEvent
  })
  .merge(HistoryEventMeta);

export type HistoryEventEntryWithMeta = z.infer<
  typeof HistoryEventEntryWithMeta
>;

export const HistoryEventsCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(HistoryEventEntryWithMeta)
});

export type HistoryEventsCollectionResponse = z.infer<
  typeof HistoryEventsCollectionResponse
>;

export interface HistoryEventEntry extends HistoryEvent, HistoryEventMeta {}
