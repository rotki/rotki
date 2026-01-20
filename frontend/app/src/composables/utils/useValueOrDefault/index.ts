import type { ComputedRef, MaybeRef, Ref } from 'vue';

export function useValueOrDefault<T, D>(item: Ref<T | undefined>, defaultValue: MaybeRef<D>): ComputedRef<T | D> {
  return computed(() => {
    const value = get(item);
    if (value)
      return value;

    return get(defaultValue);
  });
}
