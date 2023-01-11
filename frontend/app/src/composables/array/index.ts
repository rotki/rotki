import { type ComputedRef } from 'vue';
import { type MaybeRef } from '@vueuse/core';

export const useArrayInclude = <T>(
  array: MaybeRef<T[]>,
  t: MaybeRef<T>
): ComputedRef<boolean> =>
  computed(() => {
    const items = get(array);
    const item = get(t);

    return items.includes(item);
  });
