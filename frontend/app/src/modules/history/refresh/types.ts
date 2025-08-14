import type { Exchange } from '@/types/exchanges';
import type { BitcoinChainAddress, EvmChainAddress } from '@/types/history/events';
import type { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';

export type RefreshChainAddress = EvmChainAddress | BitcoinChainAddress;

export interface HistoryRefreshEventData {
  accounts?: RefreshChainAddress[];
  exchanges?: Exchange[];
  queries?: OnlineHistoryEventsQueryType[];
}

export interface ChainData {
  evmChain: string;
  id: string;
  name: string;
  type: 'evm' | 'evmlike' | 'bitcoin';
}
