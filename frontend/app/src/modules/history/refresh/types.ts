import type { Exchange } from '@/types/exchanges';
import type { ChainAddress, TransactionChainType } from '@/types/history/events';
import type { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';

export interface HistoryRefreshEventData {
  accounts?: ChainAddress[];
  exchanges?: Exchange[];
  queries?: OnlineHistoryEventsQueryType[];
}

export interface ChainData {
  chain: string;
  id: string;
  name: string;
  type: TransactionChainType;
}
