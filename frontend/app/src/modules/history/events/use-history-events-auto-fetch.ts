import type { Ref } from 'vue';
import { startPromise } from '@shared/utils';

export function useHistoryEventsAutoFetch(shouldFetch: Ref<boolean>, fetchFunction: () => Promise<void>): void {
  const { isActive, pause, resume } = useIntervalFn(() => {
    startPromise(fetchFunction());
  }, 20000);

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
