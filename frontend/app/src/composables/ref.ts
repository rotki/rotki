import type { MaybeRef } from '@vueuse/core';

export function refIsTruthy<T>(ref: MaybeRef<T>): ComputedRef<boolean> {
  return computed(() => !!get(ref));
}
