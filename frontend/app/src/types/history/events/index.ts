import type { PaginationRequestPayload } from '@/types/common';
import type { FilterObjectWithBehaviour } from '@/types/filtering';
import { CollectionCommonFields } from '@/types/collection';
import { EntryMeta } from '@/types/history/meta';
import { type BigNumber, HistoryEventEntryType, NumericString } from '@rotki/common';
import { z } from 'zod';

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

export interface PullEvmTransactionPayload {
  readonly transactions: EvmChainAndTxHash[];
  readonly deleteCustom?: boolean;
}

export interface PullEvmLikeTransactionPayload {
  readonly transactions: ChainAndTxHash[];
  readonly deleteCustom?: boolean;
}

export type PullTransactionPayload = PullEvmTransactionPayload | PullEvmLikeTransactionPayload;

export interface ChainAndTxHash {
  readonly chain: string;
  readonly txHash: string;
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
  evmChain: z.string(),
});

export type EvmChainAddress = z.infer<typeof EvmChainAddress>;

export interface RepullingTransactionPayload extends Partial<EvmChainAddress> {
  readonly fromTimestamp: number;
  readonly toTimestamp: number;
}

export interface RepullingTransactionResponse {
  newTransactionsCount: number;
}

export const EvmChainLikeAddress = z.object({
  address: z.string(),
  chain: z.string(),
});

export type EvmChainLikeAddress = z.infer<typeof EvmChainLikeAddress>;

export const HistoryEventDetail = z
  .object({
    liquityStaking: LiquityStakingEventExtraData,
  })
  .nullish();

export type HistoryEventDetail = z.infer<typeof HistoryEventDetail>;

export const CommonHistoryEvent = z.object({
  amount: NumericString,
  asset: z.string(),
  eventIdentifier: z.string(),
  eventSubtype: z.string(),
  eventType: z.string(),
  identifier: z.number(),
  location: z.string(),
  locationLabel: z.string().nullable(),
  notes: z.string().nullable().optional(),
  sequenceIndex: z.number().or(z.string()),
  timestamp: z.number(),
});

export const EvmHistoryEvent = CommonHistoryEvent.extend({
  address: z.string().nullable(),
  counterparty: z.string().nullable(),
  entryType: z.literal(HistoryEventEntryType.EVM_EVENT),
  extraData: z.unknown().nullable(),
  product: z.string().nullable(),
  txHash: z.string(),
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
  blockNumber: z.number(),
  entryType: z.literal(HistoryEventEntryType.ETH_BLOCK_EVENT),
  validatorIndex: z.number(),
});

export type EthBlockEvent = z.infer<typeof EthBlockEvent>;

export const EthDepositEvent = CommonHistoryEvent.extend({
  address: z.string().nullable(),
  counterparty: z.string().nullable(),
  entryType: z.literal(HistoryEventEntryType.ETH_DEPOSIT_EVENT),
  extraData: z.unknown().nullable(),
  product: z.string().nullable(),
  txHash: z.string(),
  validatorIndex: z.number(),
});

export type EthDepositEvent = z.infer<typeof EthDepositEvent>;

export const AssetMovementEvent = CommonHistoryEvent.extend({
  entryType: z.literal(HistoryEventEntryType.ASSET_MOVEMENT_EVENT),
  extraData: z.object({
    address: z.string().nullish(),
    reference: z.string().nullish(),
    transactionId: z.string().nullish(),
  }).nullable(),
});

export type AssetMovementEvent = z.infer<typeof AssetMovementEvent>;

export const SwapEventSchema = CommonHistoryEvent.extend({
  description: z.string(),
  entryType: z.literal(HistoryEventEntryType.SWAP_EVENT),
  extraData: z.unknown().nullable(),
});

export type SwapEvent = z.infer<typeof SwapEventSchema>;

export const HistoryEvent = EvmHistoryEvent.or(AssetMovementEvent)
  .or(OnlineHistoryEvent)
  .or(EthWithdrawalEvent)
  .or(EthBlockEvent)
  .or(EthDepositEvent)
  .or(SwapEventSchema);

export type DependentHistoryEvent = AssetMovementEvent | SwapEvent;

export type IndependentHistoryEvent = EvmHistoryEvent | OnlineHistoryEvent | EthWithdrawalEvent | EthBlockEvent | EthDepositEvent;

export type HistoryEvent = IndependentHistoryEvent | DependentHistoryEvent;

export interface AddSwapEventPayload {
  entryType: typeof HistoryEventEntryType.SWAP_EVENT;
  feeAmount?: string;
  feeAsset?: string;
  location: string;
  notes: [string, string, string] | [string, string];
  receiveAmount: string;
  receiveAsset: string;
  spendAmount: string;
  spendAsset: string;
  timestamp: number;
  uniqueId: string;
}

export interface EditSwapEventPayload extends Omit<AddSwapEventPayload, 'uniqueId'> {
  eventIdentifier: string;
  identifier: number;
}

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
  readonly identifiers?: string[];
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
  amount: BigNumber;
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
  amount: BigNumber;
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
  amount: BigNumber;
  validatorIndex: number;
  withdrawalAddress: string;
  isExit: boolean;
  eventIdentifier: string | null;
}

export type NewEthWithdrawalEventPayload = Omit<EditEthWithdrawalEventPayload, 'identifier'>;

export interface EditAssetMovementEventPayload {
  entryType: typeof HistoryEventEntryType.ASSET_MOVEMENT_EVENT;
  identifier: number;
  timestamp: number;
  amount: BigNumber;
  eventType: string;
  location: string;
  locationLabel: string | null;
  eventIdentifier: string | null;
  asset: string;
  fee: string | null;
  feeAsset: string | null;
  notes: string | null;
  uniqueId: string;
}

export type NewAssetMovementEventPayload = Omit<EditAssetMovementEventPayload, 'identifier'>;

export type EditHistoryEventPayload =
  | EditEvmHistoryEventPayload
  | EditOnlineHistoryEventPayload
  | EditEthBlockEventPayload
  | EditEthDepositEventPayload
  | EditEthWithdrawalEventPayload
  | EditAssetMovementEventPayload;

export type NewHistoryEventPayload =
  | NewEvmHistoryEventPayload
  | NewOnlineHistoryEventPayload
  | NewEthBlockEventPayload
  | NewEthDepositEventPayload
  | NewEthWithdrawalEventPayload
  | NewAssetMovementEventPayload;

export type AddHistoryEventPayload = NewHistoryEventPayload | AddSwapEventPayload;

export type ModifyHistoryEventPayload = EditHistoryEventPayload | EditSwapEventPayload;

export enum HistoryEventAccountingRuleStatus {
  HAS_RULE = 'has rule',
  NOT_PROCESSED = 'not processed',
  PROCESSED = 'processed',
}

export const HistoryEventAccountingRuleStatusEnum = z.nativeEnum(HistoryEventAccountingRuleStatus);

export const HistoryEventMeta = EntryMeta.merge(
  z.object({
    customized: z.boolean().optional(),
    defaultNotes: z.boolean().optional(),
    eventAccountingRuleStatus: HistoryEventAccountingRuleStatusEnum,
    groupedEventsNum: z.number().nullish(),
    hasDetails: z.boolean().optional(),
    hidden: z.boolean().optional(),
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
  successful: z.number(),
  total: z.number(),
});

export type ProcessSkippedHistoryEventsResponse = z.infer<typeof ProcessSkippedHistoryEventsResponse>;
