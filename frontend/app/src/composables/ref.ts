import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';

export function refIsTruthy<T>(ref: MaybeRef<T>): ComputedRef<boolean> {
  return computed(() => !!get(ref));
}
