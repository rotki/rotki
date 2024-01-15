/**
 * Returns a ComputedRef that is true if the items are undefined
 * or some item matches the condition
 * @param items
 * @param condition
 */
export function useEmptyOrSome<T>(items: Ref<T[] | undefined>, condition: (t: T) => boolean): ComputedRef<boolean> {
  return computed(() => {
    const t = get(items);
    return !t || t.some(condition);
  });
}
