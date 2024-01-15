import type { MaybeRef } from '@vueuse/core';

export function useArrayInclude<T>(array: MaybeRef<T[]>, t: MaybeRef<T>): ComputedRef<boolean> {
  return computed(() => {
    const items = get(array);
    const item = get(t);

    return items.includes(item);
  });
}
