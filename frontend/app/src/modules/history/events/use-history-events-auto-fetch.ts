import { startPromise } from '@shared/utils';
import { type Ref, ref } from 'vue';

/**
 * The refresh interval between the calls to fetch events and data.
 * It should be bigger than the request timeout to avoid queuing to many requests.
 *
 * After measurement the query to fetch the events page can take up to 20 seconds,
 * so we set the refresh interval to 60 seconds to avoid queuing too many requests.
 */
const REFRESH_INTERVAL = 60_000;

export function useHistoryEventsAutoFetch(shouldFetch: Ref<boolean>, fetchFunction: () => Promise<void>): void {
  const isFetching = ref(false);

  const { isActive, pause, resume } = useIntervalFn(() => {
    if (get(isFetching)) {
      return;
    }

    set(isFetching, true);
    startPromise(fetchFunction().finally(() => {
      set(isFetching, false);
    }));
  }, REFRESH_INTERVAL);

  watch(shouldFetch, (shouldFetch) => {
    const active = get(isActive);
    if (shouldFetch && !active)
      resume();
    else if (!shouldFetch && active)
      pause();
  });

  onUnmounted(() => {
    pause();
  });
}
