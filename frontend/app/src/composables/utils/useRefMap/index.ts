import type { ComputedRef, MaybeRefOrGetter } from 'vue';

export function useRefMap<I extends object | null | undefined, O>(inp: MaybeRefOrGetter<I>, map: (inp: I) => O): ComputedRef<O> {
  return computed(() => map(toValue(inp)));
}
