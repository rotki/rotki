import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef, Ref } from 'vue';

export function refIsTruthy<T>(ref: MaybeRef<T>): ComputedRef<boolean> {
  return computed(() => !!get(ref));
}

/**
 * Keeps a ref value true for a specified duration after it becomes false.
 * Useful for maintaining state during brief interruptions (e.g., menu staying open
 * when moving between elements).
 *
 * @param sourceRef - The source ref to watch
 * @param delay - How long to keep the value true after source becomes false (in ms)
 * @returns A computed ref that stays true during the debounce period
 */
export function useRefWithDebounce(sourceRef: Ref<boolean>, delay: number = 200): ComputedRef<boolean> {
  const debouncedRef = refDebounced(sourceRef, delay);
  return logicOr(sourceRef, debouncedRef);
}
