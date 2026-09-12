import type { Result } from 'plainfp/result';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { BankConnectionIdentity } from '@/modules/banks/types';
import type { TaskError } from '@/modules/core/tasks/task-result';
import type { ActivityId } from '@/modules/task-center/core/types';
import { useBankEventsRefresh } from '@/modules/history/events/tx/use-bank-events-refresh';
import { useExchangeEventsRefresh } from '@/modules/history/events/tx/use-exchange-events-refresh';

interface UseEventsRefreshSourcesReturn {
  queryAllBankEvents: (banks: BankConnectionIdentity[], parent?: ActivityId) => Promise<Result<void, TaskError>[]>;
  queryAllExchangeEvents: (exchanges: Exchange[], parent?: ActivityId) => Promise<Result<void, TaskError>[]>;
}

/**
 * The keyed, per-connection event sources of a history refresh: exchanges and banks. One door for
 * both, since they are refreshed the same way and the refresh handlers treat them alike.
 */
export function useEventsRefreshSources(): UseEventsRefreshSourcesReturn {
  const { queryAllExchangeEvents } = useExchangeEventsRefresh();
  const { queryAllBankEvents } = useBankEventsRefresh();
  return {
    queryAllBankEvents,
    queryAllExchangeEvents,
  };
}
