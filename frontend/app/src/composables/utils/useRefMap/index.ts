import type { ComputedRef, Ref } from 'vue';

export function useRefMap<I extends object | null | undefined, O>(inp: Ref<I>, map: (inp: I) => O): ComputedRef<O> {
  return computed(() => map(get(inp)));
}
