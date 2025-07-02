import type { ComputedRef, Ref } from 'vue';
import { useRefMap } from '@/composables/utils/useRefMap';

interface UseQueryStatusReturn<T> {
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
    if ('period' in data && data.period)
      return data.period[0] > 0;

    return false;
  };

  return {
    isQueryStatusRange,
    length,
    queryingLength,
    sortedQueryStatus,
  };
}
