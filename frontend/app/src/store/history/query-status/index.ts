import { type ComputedRef, type Ref } from 'vue';

export const useQueryStatusStore = <T>(
  isStatusFinished: (item: T) => boolean,
  createKey: (item: T) => string
) => {
  const queryStatus: Ref<Record<string, T>> = ref({});

  const resetQueryStatus = (): void => {
    set(queryStatus, {});
  };

  const isAllFinished: ComputedRef<boolean> = computed(() => {
    const statuses = get(queryStatus);
    const addresses = Object.keys(statuses);

    return addresses.every((address: string) =>
      isStatusFinished(statuses[address])
    );
  });

  const removeQueryStatus = (key: string): void => {
    const statuses = { ...get(queryStatus) };
    set(
      queryStatus,
      Object.fromEntries(
        Object.entries(statuses).filter(
          ([_, status]) => createKey(status) === key
        )
      )
    );
  };

  return {
    queryStatus,
    isAllFinished,
    removeQueryStatus,
    resetQueryStatus
  };
};
