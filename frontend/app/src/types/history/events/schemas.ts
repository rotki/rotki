import { type BigNumber, HistoryEventEntryType, NumericString } from '@rotki/common';
import { z } from 'zod/v4';
import { CollectionCommonFields } from '@/types/collection';
import { EntryMeta } from '@/types/history/meta';

const CommonHistoryEvent = z.object({
  amount: NumericString,
  asset: z.string(),
  autoNotes: z.string().optional(),
  eventSubtype: z.string(),
  eventType: z.string(),
  groupIdentifier: z.string(),
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
  extraData: z.unknown().nullish(),
  txRef: z.string(),
});

export type EvmHistoryEvent = z.infer<typeof EvmHistoryEvent>;

export const OnlineHistoryEvent = CommonHistoryEvent.extend({
  entryType: z.literal(HistoryEventEntryType.HISTORY_EVENT),
  txRef: z.string().optional(),
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
  extraData: z.unknown().nullable().nullish(),
  txRef: z.string(),
  validatorIndex: z.number(),
});

export type EthDepositEvent = z.infer<typeof EthDepositEvent>;

export const AssetMovementEvent = CommonHistoryEvent.extend({
  entryType: z.literal(HistoryEventEntryType.ASSET_MOVEMENT_EVENT),
  extraData: z.object({
    address: z.string().nullish(),
    blockchain: z.string().nullish(),
    reference: z.string().nullish(),
    transactionId: z.string().nullish(),
  }).nullable(),
});

export type AssetMovementEvent = z.infer<typeof AssetMovementEvent>;

const SwapEventSchema = CommonHistoryEvent.extend({
  entryType: z.literal(HistoryEventEntryType.SWAP_EVENT),
  extraData: z.unknown().nullable(),
});

export type SwapEvent = z.infer<typeof SwapEventSchema>;

const EvmSwapEventSchema = CommonHistoryEvent.extend({
  address: z.string().nullable(),
  counterparty: z.string().nullable(),
  entryType: z.literal(HistoryEventEntryType.EVM_SWAP_EVENT),
  extraData: z.unknown().nullable(),
  txRef: z.string(),
});

export type EvmSwapEvent = z.infer<typeof EvmSwapEventSchema>;

const SolanaEventSchema = CommonHistoryEvent.extend({
  address: z.string().nullable(),
  counterparty: z.string().nullable(),
  entryType: z.literal(HistoryEventEntryType.SOLANA_EVENT),
  extraData: z.unknown().nullish(),
  txRef: z.string(),
});

export type SolanaEvent = z.infer<typeof SolanaEventSchema>;

const SolanaSwapEventSchema = CommonHistoryEvent.extend({
  address: z.string().nullable(),
  counterparty: z.string().nullable(),
  entryType: z.literal(HistoryEventEntryType.SOLANA_SWAP_EVENT),
  extraData: z.unknown().nullish(),
  txRef: z.string(),
});

export type SolanaSwapEvent = z.infer<typeof SolanaSwapEventSchema>;

export const HistoryEvent = z.union([
  EvmHistoryEvent,
  AssetMovementEvent,
  OnlineHistoryEvent,
  EthWithdrawalEvent,
  EthBlockEvent,
  EthDepositEvent,
  SwapEventSchema,
  EvmSwapEventSchema,
  SolanaEventSchema,
  SolanaSwapEventSchema,
]);

export type GroupEditableHistoryEvents = AssetMovementEvent | SwapEvent | EvmSwapEvent | SolanaSwapEvent;

export interface FeeEntry {
  amount: string;
  asset: string;
}

export type SwapEventUserNotes = [string, string, ...string[]];

export type StandaloneEditableEvents = EvmHistoryEvent | OnlineHistoryEvent | EthWithdrawalEvent | EthBlockEvent | EthDepositEvent | SolanaEvent;

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
  fees?: FeeEntry[];
  location: string;
  userNotes: SwapEventUserNotes;
  receiveAmount: string;
  receiveAsset: string;
  spendAmount: string;
  spendAsset: string;
  timestamp: number;
  uniqueId: string;
}

export interface EditSwapEventPayload extends Omit<AddSwapEventPayload, 'uniqueId'> {
  identifiers: number[];
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
  txRef: string;
}

export interface EditEvmSwapEventPayload extends AddEvmSwapEventPayload {
  identifiers: number[];
}

export type EditEvmHistoryEventPayload = Omit<
  EvmHistoryEvent,
  'ignoredInAccounting' | 'customized' | 'groupIdentifier'
> & {
  groupIdentifier: string | null;
};

export type NewEvmHistoryEventPayload = Omit<EditEvmHistoryEventPayload, 'identifier'>;

type EditSolanaEventPayload = Omit<
  SolanaEvent,
  'ignoredInAccounting' | 'customized' | 'groupIdentifier' | 'location'
> & {
  groupIdentifier: string | null;
};

export type NewSolanaEventPayload = Omit<EditSolanaEventPayload, 'identifier'>;

type EditOnlineHistoryEventPayload = Omit<OnlineHistoryEvent, 'ignoredInAccounting' | 'customized'>;

export type NewOnlineHistoryEventPayload = Omit<EditOnlineHistoryEventPayload, 'identifier'>;

interface EditEthBlockEventPayload {
  entryType: typeof HistoryEventEntryType.ETH_BLOCK_EVENT;
  identifier: number;
  timestamp: number;
  amount: BigNumber;
  validatorIndex: number;
  blockNumber: number;
  feeRecipient: string;
  isMevReward: boolean;
  groupIdentifier: string | null;
}

export type NewEthBlockEventPayload = Omit<EditEthBlockEventPayload, 'identifier'>;

interface EditEthDepositEventPayload {
  entryType: typeof HistoryEventEntryType.ETH_DEPOSIT_EVENT;
  identifier: number;
  timestamp: number;
  amount: BigNumber;
  validatorIndex: number;
  txRef: string;
  groupIdentifier: string | null;
  sequenceIndex: number | string;
  depositor: string;
  extraData: object | null;
}

export type NewEthDepositEventPayload = Omit<EditEthDepositEventPayload, 'identifier'>;

interface EditEthWithdrawalEventPayload {
  entryType: typeof HistoryEventEntryType.ETH_WITHDRAWAL_EVENT;
  identifier: number;
  timestamp: number;
  amount: BigNumber;
  validatorIndex: number;
  withdrawalAddress: string;
  isExit: boolean;
  groupIdentifier: string | null;
}

export type NewEthWithdrawalEventPayload = Omit<EditEthWithdrawalEventPayload, 'identifier'>;

interface EditAssetMovementEventPayload {
  entryType: typeof HistoryEventEntryType.ASSET_MOVEMENT_EVENT;
  identifier: number;
  timestamp: number;
  amount: BigNumber;
  eventType: string;
  location: string;
  locationLabel: string | null;
  groupIdentifier: string | null;
  asset: string;
  fee: string | null;
  feeAsset: string | null;
  userNotes: [string, string] | [string];
  uniqueId: string;
  transactionId: string;
  blockchain: string;
}

export type NewAssetMovementEventPayload = Omit<EditAssetMovementEventPayload, 'identifier'>;

export interface AddSolanaSwapEventPayload {
  entryType: typeof HistoryEventEntryType.SOLANA_SWAP_EVENT;
  address?: string;
  timestamp: number;
  fee?: SwapSubEventModel[];
  spend: SwapSubEventModel[];
  receive: SwapSubEventModel[];
  counterparty: string;
  sequenceIndex: string;
  txRef: string;
}

export interface EditSolanaSwapEventPayload extends AddSolanaSwapEventPayload {
  identifiers: number[];
}

export type EditHistoryEventPayload =
  | EditEvmHistoryEventPayload
  | EditOnlineHistoryEventPayload
  | EditEthBlockEventPayload
  | EditEthDepositEventPayload
  | EditEthWithdrawalEventPayload
  | EditAssetMovementEventPayload
  | EditSolanaEventPayload;

export type NewHistoryEventPayload =
  | NewEvmHistoryEventPayload
  | NewOnlineHistoryEventPayload
  | NewEthBlockEventPayload
  | NewEthDepositEventPayload
  | NewEthWithdrawalEventPayload
  | NewAssetMovementEventPayload
  | NewSolanaEventPayload;

export type AddHistoryEventPayload = NewHistoryEventPayload | AddSwapEventPayload | AddEvmSwapEventPayload | AddSolanaSwapEventPayload;

export type ModifyHistoryEventPayload = EditHistoryEventPayload | EditSwapEventPayload | EditEvmSwapEventPayload | EditSolanaSwapEventPayload;

export enum HistoryEventAccountingRuleStatus {
  HAS_RULE = 'has rule',
  NOT_PROCESSED = 'not processed',
  PROCESSED = 'processed',
}

const HistoryEventAccountingRuleStatusEnum = z.enum(HistoryEventAccountingRuleStatus);

const HistoryEventMeta = z.object({
  ...EntryMeta.shape,
  customized: z.boolean().optional(),
  eventAccountingRuleStatus: HistoryEventAccountingRuleStatusEnum,
  groupedEventsNum: z.number().nullish(),
  hasDetails: z.boolean().optional(),
  hidden: z.boolean().optional(),
});

type HistoryEventMeta = z.infer<typeof HistoryEventMeta>;

const HistoryEventEntryWithMeta = z.object({
  entry: HistoryEvent,
  ...HistoryEventMeta.shape,
});

type HistoryEventEntryWithMeta = z.infer<typeof HistoryEventEntryWithMeta>;

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
  GNOSIS_PAY: 'gnosis_pay',
  MONERIUM: 'monerium',
} as const;

export type OnlineHistoryEventsQueryType = typeof OnlineHistoryEventsQueryType[keyof typeof OnlineHistoryEventsQueryType];

export interface OnlineHistoryEventsRequestPayload {
  readonly asyncQuery: boolean;
  readonly queryType: OnlineHistoryEventsQueryType;
}
