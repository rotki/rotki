export const useQueryStatus = <T extends { period?: [number, number] }>(
  data: ComputedRef<T[]>,
  isStatusFinished: (item: T) => boolean
) => {
  const sortedQueryStatus = useSorted<T>(
    data,
    (a, b) => (isStatusFinished(a) ? 1 : 0) - (isStatusFinished(b) ? 1 : 0)
  );

  const queryingLength: ComputedRef<number> = computed(
    () => get(data).filter(item => !isStatusFinished(item)).length
  );

  const length = useRefMap(data, ({ length }) => length);

  const isQueryStatusRange = (data: T) => {
    if (data.period) {
      return data.period[0] > 0;
    }
    return false;
  };

  return {
    sortedQueryStatus,
    queryingLength,
    length,
    isQueryStatusRange
  };
};
