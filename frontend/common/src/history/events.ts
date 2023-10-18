export const HistoryEventEntryType = {
  HISTORY_EVENT: 'history event',
  EVM_EVENT: 'evm event',
  ETH_WITHDRAWAL_EVENT: 'eth withdrawal event',
  ETH_BLOCK_EVENT: 'eth block event',
  ETH_DEPOSIT_EVENT: 'eth deposit event'
} as const;

export type HistoryEventEntryType =
  (typeof HistoryEventEntryType)[keyof typeof HistoryEventEntryType];
