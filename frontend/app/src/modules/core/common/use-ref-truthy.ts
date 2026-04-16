import type { ComputedRef, MaybeRef } from 'vue';

export function refIsTruthy<T>(ref: MaybeRef<T>): ComputedRef<boolean> {
  return computed(() => !!get(ref));
}
