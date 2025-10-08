export const HistoryEventEntryType = {
  ASSET_MOVEMENT_EVENT: 'asset movement event',
  ETH_BLOCK_EVENT: 'eth block event',
  ETH_DEPOSIT_EVENT: 'eth deposit event',
  ETH_WITHDRAWAL_EVENT: 'eth withdrawal event',
  EVM_EVENT: 'evm event',
  EVM_SWAP_EVENT: 'evm swap event',
  HISTORY_EVENT: 'history event',
  SOLANA_EVENT: 'solana event',
  SWAP_EVENT: 'swap event',
} as const;

export type HistoryEventEntryType = (typeof HistoryEventEntryType)[keyof typeof HistoryEventEntryType];
