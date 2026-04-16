import type { ComputedRef, MaybeRefOrGetter } from 'vue';

export function useValueOrDefault<T, D>(item: MaybeRefOrGetter<T | undefined>, defaultValue: MaybeRefOrGetter<D>): ComputedRef<T | D> {
  return computed(() => {
    const value = toValue(item);
    if (value)
      return value;

    return toValue(defaultValue);
  });
}
