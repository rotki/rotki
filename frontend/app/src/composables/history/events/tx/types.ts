import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import type { Blockchain } from '@rotki/common';

export interface RefreshTransactionsParams {
  chains?: Blockchain[];
  disableEvmEvents?: boolean;
  userInitiated?: boolean;
  payload?: HistoryRefreshEventData;
}
