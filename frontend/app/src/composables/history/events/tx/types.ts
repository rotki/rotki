import type { Blockchain } from '@rotki/common';
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import type { BitcoinChainAddress, EvmChainAddress, TransactionChainType } from '@/types/history/events';

export interface RefreshTransactionsParams {
  chains?: Blockchain[];
  disableEvmEvents?: boolean;
  userInitiated?: boolean;
  payload?: HistoryRefreshEventData;
}

export type TransactionSyncParams =
  | { accounts: EvmChainAddress[]; type: TransactionChainType.EVM | TransactionChainType.EVMLIKE }
  | { accounts: BitcoinChainAddress[]; type: TransactionChainType.BITCOIN };
