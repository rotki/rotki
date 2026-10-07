import { startPromise } from '@shared/utils';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useMessageHandling } from '@/modules/core/messaging';
import { usePeriodicDataFetcher } from '@/modules/session/use-periodic-data-fetcher';
import { useSetting } from '@/modules/settings/use-setting';
import { useWebsocketConnection } from '../use-websocket-connection';
import { useIntervalScheduler } from './use-interval-scheduler';

const SECONDS_TO_MS = 1_000;

interface UsePeriodicPollingSchedulerReturn {
  start: (immediate: boolean) => void;
  stop: () => void;
}

/**
 * Polls `/periodic` on the user's query period, and `/messages` while the websocket is down.
 *
 * @remarks
 * `/periodic` only feeds what the window shows (the last balance save, the node status), so it is
 * skipped while the window is hidden and read once as soon as it is shown again. The messages
 * keep their poll: they are the fallback for a websocket that is down, and some of them ask the
 * user something.
 */
export function usePeriodicPollingScheduler(): UsePeriodicPollingSchedulerReturn {
  const { canRequestData } = storeToRefs(useSessionAuthStore());
  const queryPeriod = useSetting('queryPeriod');
  const { check } = usePeriodicDataFetcher();
  const { consume } = useMessageHandling();
  const { connected } = useWebsocketConnection();
  const visibility = useDocumentVisibility();
  let started = false;

  function checkWhileShown(): void {
    if (get(canRequestData) && get(visibility) === 'visible')
      startPromise(check());
  }

  function fetch(): void {
    checkWhileShown();

    if (!get(connected))
      startPromise(consume());
  }

  const scheduler = useIntervalScheduler({
    callback: fetch,
    intervalMs: () => get(queryPeriod) * SECONDS_TO_MS,
  });

  watch(visibility, () => {
    if (started)
      checkWhileShown();
  });

  return {
    start: (immediate: boolean): void => {
      started = true;
      scheduler.start(immediate);
    },
    stop: (): void => {
      started = false;
      scheduler.stop();
    },
  };
}
