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
  readonly accounts: BlockchainAddress[];
}

export interface PullEvmTransactionPayload {
  readonly transactions: EvmChainAndTxHash[];
  readonly deleteCustom?: boolean;
}

export interface PullEthBlockEventPayload {
  readonly blockNumbers: number[];
}

export type PullEventPayload = {
  type: typeof HistoryEventEntryType.ETH_BLOCK_EVENT;
  data: number [];
} | {
  type: typeof HistoryEventEntryType.EVM_SWAP_EVENT | typeof HistoryEventEntryType.EVM_EVENT;
  data: EvmChainAndTxHash;
};

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

export const BlockchainAddress = z.object({
  address: z.string(),
  blockchain: z.string().optional(),
});

export type BlockchainAddress = z.infer<typeof BlockchainAddress>;

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
  autoNotes: z.string().optional(),
  eventIdentifier: z.string(),
  eventSubtype: z.string(),
  eventType: z.string(),
  identifier: z.number(),
  location: z.string(),
  locationLabel: z.string().nullable(),
  sequenceIndex: z.number().or(z.string()),
  timestamp: z.number(),
  userNotes: z.string().optional(),
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
  entryType: z.literal(HistoryEventEntryType.SWAP_EVENT),
  extraData: z.unknown().nullable(),
});

export type SwapEvent = z.infer<typeof SwapEventSchema>;

export const EvmSwapEventSchema = CommonHistoryEvent.extend({
  address: z.string().nullable(),
  counterparty: z.string().nullable(),
  entryType: z.literal(HistoryEventEntryType.EVM_SWAP_EVENT),
  extraData: z.unknown().nullable(),
  txHash: z.string(),
});

export type EvmSwapEvent = z.infer<typeof EvmSwapEventSchema>;

export const HistoryEvent = EvmHistoryEvent.or(AssetMovementEvent)
  .or(OnlineHistoryEvent)
  .or(EthWithdrawalEvent)
  .or(EthBlockEvent)
  .or(EthDepositEvent)
  .or(SwapEventSchema)
  .or(EvmSwapEventSchema);

export type GroupEditableHistoryEvents = AssetMovementEvent | SwapEvent | EvmSwapEvent;

export type StandaloneEditableEvents = EvmHistoryEvent | OnlineHistoryEvent | EthWithdrawalEvent | EthBlockEvent | EthDepositEvent;

export type HistoryEvent = StandaloneEditableEvents | GroupEditableHistoryEvents;

export interface SwapSubEventModel {
  identifier?: number;
  amount: string;
  asset: string;
  userNotes?: string;
  locationLabel?: string;
}

export interface AddSwapEventPayload {
  entryType: typeof HistoryEventEntryType.SWAP_EVENT;
  feeAmount?: string;
  feeAsset?: string;
  location: string;
  userNotes: [string, string, string] | [string, string];
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

export interface AddEvmSwapEventPayload {
  entryType: typeof HistoryEventEntryType.EVM_SWAP_EVENT;
  address?: string;
  location: string;
  timestamp: number;
  fee?: SwapSubEventModel[];
  spend: SwapSubEventModel[];
  receive: SwapSubEventModel[];
  counterparty: string;
  sequenceIndex: string;
  txHash: string;
}

export interface EditEvmSwapEventPayload extends AddEvmSwapEventPayload {
  identifiers: number[];
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
  userNotes: [string, string] | [string];
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

export type AddHistoryEventPayload = NewHistoryEventPayload | AddSwapEventPayload | AddEvmSwapEventPayload;

export type ModifyHistoryEventPayload = EditHistoryEventPayload | EditSwapEventPayload | EditEvmSwapEventPayload;

export enum HistoryEventAccountingRuleStatus {
  HAS_RULE = 'has rule',
  NOT_PROCESSED = 'not processed',
  PROCESSED = 'processed',
}

export const HistoryEventAccountingRuleStatusEnum = z.nativeEnum(HistoryEventAccountingRuleStatus);

export const HistoryEventMeta = EntryMeta.merge(
  z.object({
    customized: z.boolean().optional(),
    eventAccountingRuleStatus: HistoryEventAccountingRuleStatusEnum,
    groupedEventsNum: z.number().nullish(),
    hasDetails: z.boolean().optional(),
    hidden: z.boolean().optional(),
  }),
);

export type HistoryEventMeta = z.infer<typeof HistoryEventMeta>;

const HistoryEventEntryWithMeta = z.object({ entry: HistoryEvent }).merge(HistoryEventMeta);

export type HistoryEventEntryWithMeta = z.infer<typeof HistoryEventEntryWithMeta>;

const HistoryEventCollectionRowSchema = z.array(HistoryEventEntryWithMeta.or(z.array(HistoryEventEntryWithMeta)));

export type HistoryEventCollectionRow = HistoryEventEntryWithMeta | HistoryEventEntryWithMeta[];

export const HistoryEventsCollectionResponse = CollectionCommonFields.extend({
  entries: HistoryEventCollectionRowSchema,
});

export type HistoryEventsCollectionResponse = z.infer<typeof HistoryEventsCollectionResponse>;

export type HistoryEventEntry = HistoryEvent & HistoryEventMeta;

export type HistoryEventRow = HistoryEventEntry | HistoryEventEntry[];

export const OnlineHistoryEventsQueryType = {
  BLOCK_PRODUCTIONS: 'block_productions',
  ETH_WITHDRAWALS: 'eth_withdrawals',
} as const;

export type OnlineHistoryEventsQueryType = typeof OnlineHistoryEventsQueryType[keyof typeof OnlineHistoryEventsQueryType];

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
