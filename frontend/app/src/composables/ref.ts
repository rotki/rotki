import { type MaybeRef } from '@vueuse/core';

export const refIsTruthy = <T>(ref: MaybeRef<T>): ComputedRef<boolean> =>
  computed(() => !!get(ref));
