import type { MaybeRef } from '@vueuse/core';
import type { ModelRef } from 'vue';

export function useFormStateWatcher(
  states: Record<string, MaybeRef<any>>,
  stateUpdated: ModelRef<boolean>,
): void {
  setTimeout(() => {
    watch(
      () => states,
      () => {
        set(stateUpdated, true);
      },
      { deep: true, once: true },
    );
  }, 500);

  onUnmounted(() => {
    set(stateUpdated, false);
  });
}
