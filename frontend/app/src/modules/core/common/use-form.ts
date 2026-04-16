import type { MaybeRef, ModelRef } from 'vue';

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
