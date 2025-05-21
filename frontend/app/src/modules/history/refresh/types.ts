import type { Exchange } from '@/types/exchanges';
import type { EvmChainAddress, OnlineHistoryEventsQueryType } from '@/types/history/events';

export interface HistoryRefreshEventData {
  accounts?: EvmChainAddress[];
  exchanges?: Exchange[];
  queries?: OnlineHistoryEventsQueryType[];
}

export interface ChainData {
  evmChain: string;
  id: string;
  name: string;
  type: 'evm' | 'evmlike';
}
