import { Balance, HistoryEventEntryType, NumericString } from '@rotki/common';
import { z } from 'zod';
import { EntryMeta } from '@/types/history/meta';
import { CollectionCommonFields } from '@/types/collection';
import type { PaginationRequestPayload } from '@/types/common';
import type { FilterObjectWithBehaviour } from '@/types/filtering';

const LiquityStakingEventExtraData = z.object({
  asset: z.string(),
  stakedAmount: NumericString,
});

export enum TransactionChainType {
  EVM = 'evm',
  EVMLIKE = 'evmlike',
}

export interface TransactionRequestPayload {
  readonly accounts: EvmChainAddress[];
}

export interface TransactionHashAndEvmChainPayload {
  readonly txHashes?: string[] | null;
  readonly evmChain: string;
}

export interface AddressesAndEvmChainPayload {
  readonly addresses?: string[] | null;
  readonly evmChain: string;
}

export interface ChainAndTxHash {
  readonly chain: string;
  readonly txHash: string;
}

export interface EvmChainAndTxHash {
  readonly evmChain: string;
  readonly txHash: string;
  readonly deleteCustom?: boolean;
}

export interface AddTransactionHashPayload extends EvmChainAndTxHash {
  readonly associatedAddress: string;
}

export const EvmChainAddress = z.object({
  address: z.string(),
  evmChain: z.string(),
});

export type EvmChainAddress = z.infer<typeof EvmChainAddress>;

export const EvmChainLikeAddress = z.object({
  address: z.string(),
  chain: z.string(),
});

export type EvmChainLikeAddress = z.infer<typeof EvmChainLikeAddress>;

export interface TransactionEventRequestPayload {
  readonly data: TransactionHashAndEvmChainPayload[];
  readonly ignoreCache: boolean;
}

export const HistoryEventDetail = z
  .object({
    liquityStaking: LiquityStakingEventExtraData,
  })
  .nullish();

export type HistoryEventDetail = z.infer<typeof HistoryEventDetail>;

export const CommonHistoryEvent = z.object({
  identifier: z.number(),
  eventIdentifier: z.string(),
  sequenceIndex: z.number().or(z.string()),
  timestamp: z.number(),
  location: z.string(),
  asset: z.string(),
  balance: Balance,
  eventType: z.string(),
  eventSubtype: z.string(),
  locationLabel: z.string().nullable(),
  notes: z.string().nullable().optional(),
});

export const EvmHistoryEvent = CommonHistoryEvent.extend({
  entryType: z.literal(HistoryEventEntryType.EVM_EVENT),
  address: z.string().nullable(),
  counterparty: z.string().nullable(),
  product: z.string().nullable(),
  txHash: z.string(),
  extraData: z.unknown().nullable(),
});

export type EvmHistoryEvent = z.infer<typeof EvmHistoryEvent>;

export const OnlineHistoryEvent = CommonHistoryEvent.extend({
  entryType: z.literal(HistoryEventEntryType.HISTORY_EVENT),
});

export type OnlineHistoryEvent = z.infer<typeof OnlineHistoryEvent>;

export const EthWithdrawalEvent = CommonHistoryEvent.extend({
  entryType: z.literal(HistoryEventEntryType.ETH_WITHDRAWAL_EVENT),
  isExit: z.boolean(),
  validatorIndex: z.number(),
});

export type EthWithdrawalEvent = z.infer<typeof EthWithdrawalEvent>;

export const EthBlockEvent = CommonHistoryEvent.extend({
  entryType: z.literal(HistoryEventEntryType.ETH_BLOCK_EVENT),
  blockNumber: z.number(),
  validatorIndex: z.number(),
});

export type EthBlockEvent = z.infer<typeof EthBlockEvent>;

export const EthDepositEvent = CommonHistoryEvent.extend({
  entryType: z.literal(HistoryEventEntryType.ETH_DEPOSIT_EVENT),
  address: z.string().nullable(),
  counterparty: z.string().nullable(),
  product: z.string().nullable(),
  txHash: z.string(),
  validatorIndex: z.number(),
  extraData: z.unknown().nullable(),
});

export type EthDepositEvent = z.infer<typeof EthDepositEvent>;

export const HistoryEvent = EvmHistoryEvent.or(OnlineHistoryEvent)
  .or(EthWithdrawalEvent)
  .or(EthBlockEvent)
  .or(EthDepositEvent);

export type HistoryEvent = EvmHistoryEvent | OnlineHistoryEvent | EthWithdrawalEvent | EthBlockEvent | EthDepositEvent;

export interface HistoryEventRequestPayload extends PaginationRequestPayload<{ timestamp: number }> {
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
  readonly products?: string | string[];
  readonly entryTypes?: FilterObjectWithBehaviour<string | string[]>;
  readonly txHashes?: string | string[];
  readonly validatorIndices?: string | string[];
  readonly customizedEventsOnly?: boolean;
  readonly excludeIgnoredAssets?: boolean;
}

export type EditEvmHistoryEventPayload = Omit<
  EvmHistoryEvent,
  'ignoredInAccounting' | 'customized' | 'eventIdentifier'
> & {
  eventIdentifier: string | null;
};

export type NewEvmHistoryEventPayload = Omit<EditEvmHistoryEventPayload, 'identifier'>;

export type EditOnlineHistoryEventPayload = Omit<OnlineHistoryEvent, 'ignoredInAccounting' | 'customized'>;

export type NewOnlineHistoryEventPayload = Omit<EditOnlineHistoryEventPayload, 'identifier'>;

export interface EditEthBlockEventPayload {
  entryType: typeof HistoryEventEntryType.ETH_BLOCK_EVENT;
  identifier: number;
  timestamp: number;
  balance: Balance;
  validatorIndex: number;
  blockNumber: number;
  feeRecipient: string;
  isMevReward: boolean;
  eventIdentifier: string | null;
}

export type NewEthBlockEventPayload = Omit<EditEthBlockEventPayload, 'identifier'>;

export interface EditEthDepositEventPayload {
  entryType: typeof HistoryEventEntryType.ETH_DEPOSIT_EVENT;
  identifier: number;
  timestamp: number;
  balance: Balance;
  validatorIndex: number;
  txHash: string;
  eventIdentifier: string | null;
  sequenceIndex: number | string;
  depositor: string;
  extraData: object | null;
}

export type NewEthDepositEventPayload = Omit<EditEthDepositEventPayload, 'identifier'>;

export interface EditEthWithdrawalEventPayload {
  entryType: typeof HistoryEventEntryType.ETH_WITHDRAWAL_EVENT;
  identifier: number;
  timestamp: number;
  balance: Balance;
  validatorIndex: number;
  withdrawalAddress: string;
  isExit: boolean;
  eventIdentifier: string | null;
}

export type NewEthWithdrawalEventPayload = Omit<EditEthWithdrawalEventPayload, 'identifier'>;

export type EditHistoryEventPayload =
  | EditEvmHistoryEventPayload
  | EditOnlineHistoryEventPayload
  | EditEthBlockEventPayload
  | EditEthDepositEventPayload
  | EditEthWithdrawalEventPayload;

export type NewHistoryEventPayload =
  | NewEvmHistoryEventPayload
  | NewOnlineHistoryEventPayload
  | NewEthBlockEventPayload
  | NewEthDepositEventPayload
  | NewEthWithdrawalEventPayload;

export enum HistoryEventAccountingRuleStatus {
  HAS_RULE = 'has rule',
  NOT_PROCESSED = 'not processed',
  PROCESSED = 'processed',
}

export const HistoryEventAccountingRuleStatusEnum = z.nativeEnum(HistoryEventAccountingRuleStatus);

export const HistoryEventMeta = EntryMeta.merge(
  z.object({
    customized: z.boolean().optional(),
    hasDetails: z.boolean().optional(),
    hidden: z.boolean().optional(),
    groupedEventsNum: z.number().nullish(),
    eventAccountingRuleStatus: HistoryEventAccountingRuleStatusEnum,
    defaultNotes: z.boolean().optional(),
  }),
);

export type HistoryEventMeta = z.infer<typeof HistoryEventMeta>;

const HistoryEventEntryWithMeta = z
  .object({
    entry: HistoryEvent,
  })
  .merge(HistoryEventMeta);

export type HistoryEventEntryWithMeta = z.infer<typeof HistoryEventEntryWithMeta>;

export const HistoryEventsCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(HistoryEventEntryWithMeta),
});

export type HistoryEventsCollectionResponse = z.infer<typeof HistoryEventsCollectionResponse>;

export type HistoryEventEntry = HistoryEvent & HistoryEventMeta;

export enum OnlineHistoryEventsQueryType {
  ETH_WITHDRAWALS = 'eth_withdrawals',
  BLOCK_PRODUCTIONS = 'block_productions',
  EXCHANGES = 'exchanges',
}

export interface OnlineHistoryEventsRequestPayload {
  readonly asyncQuery: boolean;
  readonly queryType: OnlineHistoryEventsQueryType;
}

export const SkippedHistoryEventsSummary = z.object({
  locations: z.record(z.number()),
  total: z.number(),
});

export type SkippedHistoryEventsSummary = z.infer<typeof SkippedHistoryEventsSummary>;

export const ProcessSkippedHistoryEventsResponse = z.object({
  total: z.number(),
  successful: z.number(),
});

export type ProcessSkippedHistoryEventsResponse = z.infer<typeof ProcessSkippedHistoryEventsResponse>;

export interface ShowMissingRuleForm {
  readonly type: 'missingRule';
  readonly data: {
    group: HistoryEventEntry;
    event: HistoryEventEntry;
  };
}

export interface ShowEventForm {
  readonly type: 'event';
  readonly data: {
    group?: HistoryEvent;
    event?: HistoryEvent;
    nextSequenceId?: string;
  };
}

export type ShowEventHistoryForm = ShowEventForm | ShowMissingRuleForm;
