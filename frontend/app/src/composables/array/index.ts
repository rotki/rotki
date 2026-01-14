import type { ComputedRef, MaybeRef } from 'vue';

export function useArrayInclude<T>(array: MaybeRef<T[]>, t: MaybeRef<T>): ComputedRef<boolean> {
  return computed(() => {
    const items = get(array);
    const item = get(t);

    return items.includes(item);
  });
}
