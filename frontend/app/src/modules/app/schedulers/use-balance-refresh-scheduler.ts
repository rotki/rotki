import { startPromise } from '@shared/utils';
import { useBalanceFetching } from '@/modules/balances/use-balance-fetching';
import { useSessionAuthStore } from '@/modules/session/use-session-auth-store';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useIntervalScheduler } from './use-interval-scheduler';

const MINUTES_TO_MS = 60 * 1_000;

interface UseBalanceRefreshSchedulerReturn {
  start: () => void;
  stop: () => void;
}

export function useBalanceRefreshScheduler(): UseBalanceRefreshSchedulerReturn {
  const { canRequestData } = storeToRefs(useSessionAuthStore());
  const { refreshPeriod } = storeToRefs(useFrontendSettingsStore());
  const { autoRefresh } = useBalanceFetching();

  const period = get(refreshPeriod) * MINUTES_TO_MS;

  const scheduler = useIntervalScheduler({
    callback(): void {
      if (get(canRequestData))
        startPromise(autoRefresh());
    },
    intervalMs: Math.max(period, 1),
  });

  function start(): void {
    if (import.meta.env.VITE_NO_AUTO_FETCH === 'true')
      return;

    if (period > 0)
      scheduler.start();
  }

  return {
    start,
    stop: scheduler.stop,
  };
}
