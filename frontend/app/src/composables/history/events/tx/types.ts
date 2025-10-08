import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import type { ChainAddress, TransactionChainType } from '@/types/history/events';

export interface RefreshTransactionsParams {
  chains?: string[];
  disableEvmEvents?: boolean;
  userInitiated?: boolean;
  payload?: HistoryRefreshEventData;
}

export interface TransactionSyncParams { accounts: ChainAddress[]; type: TransactionChainType }
