/**
 * The payloads the history event forms send to add or edit events, one per entry type, and the
 * unions the api client accepts. Split from the event schemas, which describe what comes back.
 */
import type { BigNumber, HistoryEventEntryType } from '@rotki/common';
import type {
  BankTransactionEvent,
  BitcoinEvent,
  EvmHistoryEvent,
  OnlineHistoryEvent,
  SolanaEvent,
} from '@/modules/history/events/schemas';

interface FeeEntry {
  amount: string;
  asset: string;
}

export type SwapEventUserNotes = [string, string, ...string[]];

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
  'ignoredInAccounting' | 'states' | 'groupIdentifier'
> & {
  groupIdentifier: string | null;
};

export type NewEvmHistoryEventPayload = Omit<EditEvmHistoryEventPayload, 'identifier'>;

type EditSolanaEventPayload = Omit<
  SolanaEvent,
  'ignoredInAccounting' | 'states' | 'groupIdentifier' | 'location'
> & {
  groupIdentifier: string | null;
};

export type NewSolanaEventPayload = Omit<EditSolanaEventPayload, 'identifier'>;

type EditBitcoinEventPayload = Omit<
  BitcoinEvent,
  'ignoredInAccounting' | 'states' | 'groupIdentifier' | 'address'
> & {
  groupIdentifier: string | null;
};

export type NewBitcoinEventPayload = Omit<EditBitcoinEventPayload, 'identifier'>;

type EditOnlineHistoryEventPayload = Omit<OnlineHistoryEvent, 'ignoredInAccounting' | 'states'>;

export type NewOnlineHistoryEventPayload = Omit<EditOnlineHistoryEventPayload, 'identifier'>;

type EditBankTransactionEventPayload = Omit<BankTransactionEvent, 'ignoredInAccounting' | 'states'>;

export type NewBankTransactionEventPayload = Omit<EditBankTransactionEventPayload, 'identifier'>;

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
  eventSubtype: string;
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
  | EditBankTransactionEventPayload
  | EditEthBlockEventPayload
  | EditEthDepositEventPayload
  | EditEthWithdrawalEventPayload
  | EditAssetMovementEventPayload
  | EditSolanaEventPayload
  | EditBitcoinEventPayload;

export type NewHistoryEventPayload =
  | NewEvmHistoryEventPayload
  | NewOnlineHistoryEventPayload
  | NewBankTransactionEventPayload
  | NewEthBlockEventPayload
  | NewEthDepositEventPayload
  | NewEthWithdrawalEventPayload
  | NewAssetMovementEventPayload
  | NewSolanaEventPayload
  | NewBitcoinEventPayload;
