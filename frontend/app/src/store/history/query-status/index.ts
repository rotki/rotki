import type { ComputedRef, Ref } from 'vue';

interface UseQueryStatusStoreReturn<T> {
  queryStatus: Ref<Record<string, T>>;
  isAllFinished: ComputedRef<boolean>;
  removeQueryStatus: (key: string) => void;
  resetQueryStatus: () => void;
}

export function useQueryStatusStore<T>(isStatusFinished: (item: T) => boolean, createKey: (item: T) => string): UseQueryStatusStoreReturn<T> {
  const queryStatus = ref<Record<string, T>>({});

  const resetQueryStatus = (): void => {
    set(queryStatus, {});
  };

  const isAllFinished = computed<boolean>(() => {
    const statuses = get(queryStatus);
    const addresses = Object.keys(statuses);

    return addresses.every((address: string) => isStatusFinished(statuses[address]));
  });

  const removeQueryStatus = (key: string): void => {
    const statuses = { ...get(queryStatus) };
    set(queryStatus, Object.fromEntries(Object.entries(statuses).filter(([_, status]) => createKey(status) === key)));
  };

  return {
    isAllFinished,
    queryStatus,
    removeQueryStatus,
    resetQueryStatus,
  };
}
