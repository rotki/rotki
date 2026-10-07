import { startPromise } from '@shared/utils';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useBalanceFetching } from '@/modules/balances/use-balance-fetching';
import { useSetting } from '@/modules/settings/use-setting';
import { useIntervalScheduler } from './use-interval-scheduler';

const MINUTES_TO_MS = 60 * 1_000;

interface UseBalanceRefreshSchedulerReturn {
  start: () => void;
  stop: () => void;
}

export function useBalanceRefreshScheduler(): UseBalanceRefreshSchedulerReturn {
  const { canRequestData } = storeToRefs(useSessionAuthStore());
  const refreshPeriod = useSetting('refreshPeriod');
  const { autoRefresh } = useBalanceFetching();

  const scheduler = useIntervalScheduler({
    callback(): void {
      if (get(canRequestData))
        startPromise(autoRefresh());
    },
    intervalMs: () => get(refreshPeriod) * MINUTES_TO_MS,
  });

  function start(): void {
    if (import.meta.env.VITE_NO_AUTO_FETCH === 'true')
      return;

    scheduler.start();
  }

  return {
    start,
    stop: scheduler.stop,
  };
}
