import type { ComputedRef, MaybeRefOrGetter } from 'vue';

/**
 * Keeps a value true for a specified duration after it becomes false.
 * Useful for maintaining state during brief interruptions (e.g., menu staying open
 * when moving between elements).
 *
 * @param sourceRef - The source value, ref, or getter to watch
 * @param delay - How long to keep the value true after source becomes false (in ms)
 * @returns A computed ref that stays true during the debounce period
 */
export function useRefWithDebounce(sourceRef: MaybeRefOrGetter<boolean>, delay: number = 200): ComputedRef<boolean> {
  // refDebounced only accepts a Ref, so normalize the input once.
  const source = toRef(sourceRef);
  const debouncedRef = refDebounced(source, delay);
  return logicOr(source, debouncedRef);
}
