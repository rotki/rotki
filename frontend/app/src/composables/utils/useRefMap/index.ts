export const useRefMap = <I extends object | null, O>(
  inp: Ref<I>,
  map: (inp: I) => O
): ComputedRef<O> => computed(() => map(get(inp)));
