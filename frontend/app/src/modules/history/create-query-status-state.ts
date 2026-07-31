import type { ComputedRef, Ref } from 'vue';

interface QueryStatusStateReturn<T> {
  queryStatus: Ref<Record<string, T>>;
  syncing: Ref<boolean>;
  isAllFinished: ComputedRef<boolean>;
  /** Replace an entry's status with a terminal one (cancelled, failed) instead of dropping it. */
  markTerminal: (key: string, terminalStatus: T) => void;
  removeQueryStatus: (key: string) => void;
  resetQueryStatus: () => void;
  stopSyncing: () => void;
}

export function createQueryStatusState<T>(isStatusFinished: (item: T) => boolean, createKey: (item: T) => string): QueryStatusStateReturn<T> {
  const queryStatus = ref<Record<string, T>>({});
  const syncing = ref<boolean>(false);

  const resetQueryStatus = (): void => {
    set(queryStatus, {});
    set(syncing, false);
  };

  const stopSyncing = (): void => {
    set(syncing, false);
  };

  const markTerminal = (key: string, terminalStatus: T): void => {
    const statuses = { ...get(queryStatus) };
    if (statuses[key]) {
      statuses[key] = terminalStatus;
      set(queryStatus, statuses);
    }
  };

  const isAllFinished = computed<boolean>(() => {
    const statuses = get(queryStatus);
    const keys = Object.keys(statuses);

    return keys.every((key: string) => isStatusFinished(statuses[key]));
  });

  const removeQueryStatus = (key: string): void => {
    const statuses = { ...get(queryStatus) };
    set(queryStatus, Object.fromEntries(Object.entries(statuses).filter(([_, status]) => createKey(status) !== key)));
  };

  return {
    isAllFinished,
    markTerminal,
    queryStatus,
    removeQueryStatus,
    resetQueryStatus,
    stopSyncing,
    syncing,
  };
}
