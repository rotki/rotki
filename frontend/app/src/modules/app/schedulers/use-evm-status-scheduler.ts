import { startPromise } from '@shared/utils';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { useSessionAuthStore } from '@/modules/session/use-session-auth-store';
import { useIntervalScheduler } from './use-interval-scheduler';

const EVM_STATUS_POLLING_MS = 10 * 60 * 1_000;

interface UseEvmStatusSchedulerReturn {
  start: () => void;
  stop: () => void;
}

export function useEvmStatusScheduler(): UseEvmStatusSchedulerReturn {
  const { canRequestData } = storeToRefs(useSessionAuthStore());
  const { fetchTransactionStatusSummary } = useHistoryDataFetching();

  const scheduler = useIntervalScheduler({
    callback(): void {
      if (get(canRequestData))
        startPromise(fetchTransactionStatusSummary());
    },
    intervalMs: EVM_STATUS_POLLING_MS,
  });

  return {
    start: (): void => scheduler.start(get(canRequestData)),
    stop: scheduler.stop,
  };
}
