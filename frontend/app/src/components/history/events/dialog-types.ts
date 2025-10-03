import type {
  GroupEventData,
  HistoryEventEditData,
  StandaloneEventData,
} from '@/modules/history/management/forms/form-types';
import type { Exchange } from '@/types/exchanges';
import type { AddTransactionHashPayload, EvmChainAndTxHash } from '@/types/history/events';
import type { AccountingRuleEntry } from '@/types/settings/accounting';

export const DIALOG_TYPES = {
  ADD_MISSING_RULE: 'addMissingRule',
  ADD_TRANSACTION: 'addTransaction',
  DECODING_STATUS: 'decodingStatus',
  EVENT_FORM: 'eventForm',
  MISSING_RULES: 'missingRules',
  PROTOCOL_CACHE: 'protocolCache',
  REPULLING_TRANSACTION: 'repullingTransaction',
  TRANSACTION_FORM: 'transactionForm',
} as const;

export type DialogType = typeof DIALOG_TYPES[keyof typeof DIALOG_TYPES];

export type DialogShowOptions =
  | { type: typeof DIALOG_TYPES.ADD_MISSING_RULE; data: Pick<AccountingRuleEntry, 'eventType' | 'eventSubtype' | 'counterparty'> }
  | { type: typeof DIALOG_TYPES.EVENT_FORM; data: GroupEventData | StandaloneEventData }
  | { type: typeof DIALOG_TYPES.TRANSACTION_FORM; data?: AddTransactionHashPayload }
  | { type: typeof DIALOG_TYPES.REPULLING_TRANSACTION }
  | { type: typeof DIALOG_TYPES.MISSING_RULES; data: HistoryEventEditData }
  | { type: typeof DIALOG_TYPES.DECODING_STATUS; persistent?: boolean }
  | { type: typeof DIALOG_TYPES.PROTOCOL_CACHE }
  | { type: typeof DIALOG_TYPES.ADD_TRANSACTION };

// Type-safe event handlers based on dialog types
// Common toggle options for history events filtering
export interface HistoryEventsToggles {
  customizedEventsOnly: boolean;
  showIgnoredAssets: boolean;
  matchExactEvents: boolean;
}

export interface DialogEventHandlers {
  onHistoryEventSaved?: () => void | Promise<void>;
  onTransactionAdded?: (txHash: EvmChainAndTxHash) => void | Promise<void>;
  onRepullTransactions?: (chains: string[]) => void | Promise<void>;
  onRepullExchangeEvents?: (exchanges: Exchange[]) => Promise<void>;
  onRedecodeTransaction?: (txHash: EvmChainAndTxHash) => void | Promise<void>;
  onRedecodeAllEvents?: () => void | Promise<void>;
  onResetUndecodedTransactions?: () => void | Promise<void>;
}
