import { type ComputedRef } from 'vue';

export const useRefMap = <I extends object | null, O>(
  inp: ComputedRef<I>,
  map: (inp: I) => O
): ComputedRef<O> => computed(() => map(get(inp)));
