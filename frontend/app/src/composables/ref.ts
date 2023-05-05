import { type MaybeRef } from '@vueuse/core';
import { type ComputedRef } from 'vue';

export const refIsTruthy = <T>(ref: MaybeRef<T>): ComputedRef<boolean> =>
  computed(() => !!get(ref));
