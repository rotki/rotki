import type { Exchange } from '@/modules/balances/types/exchanges';
import type { BankConnectionIdentity } from '@/modules/banks/types';
import type { ChainAddress, TransactionChainType } from '@/modules/history/events/event-payloads';
import type { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';

export interface HistoryRefreshEventData {
  accounts?: ChainAddress[];
  banks?: BankConnectionIdentity[];
  exchanges?: Exchange[];
  queries?: OnlineHistoryEventsQueryType[];
}

export interface ChainData {
  chain: string;
  id: string;
  name: string;
  type: TransactionChainType;
}
