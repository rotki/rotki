interface UseQueryStatusReturn<T extends { period?: [number, number] }> {
  sortedQueryStatus: Ref<T[]>;
  queryingLength: ComputedRef<number>;
  length: ComputedRef<number>;
  isQueryStatusRange: (data: T) => boolean;
}

export function useQueryStatus<T extends { period?: [number, number] }>(
  data: ComputedRef<T[]>,
  isStatusFinished: (item: T) => boolean,
): UseQueryStatusReturn<T> {
  const sortedQueryStatus = useSorted<T>(data, (a, b) => (isStatusFinished(a) ? 1 : 0) - (isStatusFinished(b) ? 1 : 0));

  const queryingLength = computed<number>(
    () => get(data).filter(item => !isStatusFinished(item)).length,
  );

  const length = useRefMap(data, ({ length }) => length);

  const isQueryStatusRange = (data: T): boolean => {
    if (data.period)
      return data.period[0] > 0;

    return false;
  };

  return {
    sortedQueryStatus,
    queryingLength,
    length,
    isQueryStatusRange,
  };
}
