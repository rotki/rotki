import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';

export interface RefreshTransactionsParams {
  chains?: string[];
  disableEvmEvents?: boolean;
  userInitiated?: boolean;
  payload?: HistoryRefreshEventData;
}
