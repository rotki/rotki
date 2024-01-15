import type { MaybeRef } from '@vueuse/core';

export function useValueOrDefault<T, D>(item: Ref<T | undefined>, defaultValue: MaybeRef<D>): ComputedRef<T | D> {
  return computed(() => {
    const value = get(item);
    if (value)
      return value;

    return get(defaultValue);
  });
}
