export function useComputedRef<I extends object, K extends keyof I>(inp: Ref<I>, prop: K): ComputedRef<I[K]> {
  return computed(() => get(inp)[prop]);
}
