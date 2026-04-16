import { startPromise } from '@shared/utils';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useMessageHandling } from '@/modules/core/messaging';
import { usePeriodicDataFetcher } from '@/modules/session/use-periodic-data-fetcher';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useWebsocketConnection } from '../use-websocket-connection';
import { useIntervalScheduler } from './use-interval-scheduler';

const SECONDS_TO_MS = 1_000;

interface UsePeriodicPollingSchedulerReturn {
  start: (immediate: boolean) => void;
  stop: () => void;
}

export function usePeriodicPollingScheduler(): UsePeriodicPollingSchedulerReturn {
  const { canRequestData } = storeToRefs(useSessionAuthStore());
  const { queryPeriod } = storeToRefs(useFrontendSettingsStore());
  const { check } = usePeriodicDataFetcher();
  const { consume } = useMessageHandling();
  const { connected } = useWebsocketConnection();

  function fetch(): void {
    if (get(canRequestData))
      startPromise(check());

    if (!get(connected))
      startPromise(consume());
  }

  const scheduler = useIntervalScheduler({
    callback: fetch,
    intervalMs: get(queryPeriod) * SECONDS_TO_MS,
  });

  return {
    start: (immediate: boolean): void => scheduler.start(immediate),
    stop: scheduler.stop,
  };
}
