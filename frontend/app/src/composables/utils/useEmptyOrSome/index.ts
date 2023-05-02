/**
 * Returns a ComputedRef that is true if the items are undefined
 * or some item matches the condition
 * @param items
 * @param condition
 */
export const useEmptyOrSome = <T>(
  items: Ref<T[] | undefined>,
  condition: (t: T) => boolean
): ComputedRef<boolean> =>
  computed(() => {
    const t = get(items);
    return !t || t.some(condition);
  });
