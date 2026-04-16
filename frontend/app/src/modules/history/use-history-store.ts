import type { LocationLabel } from '@/modules/core/common/location';
import type { TransactionStatus } from '@/modules/history/api/events/use-history-events-api';

export const useHistoryStore = defineStore('history', () => {
  const associatedLocations = shallowRef<string[]>([]);
  const locationLabels = shallowRef<LocationLabel[]>([]);
  const transactionStatusSummary = shallowRef<TransactionStatus>();

  const eventsVersion = ref<number>(0);
  const acknowledgedVersion = ref<number>(0);

  const hasUnprocessedModifications = computed<boolean>(() =>
    get(eventsVersion) > get(acknowledgedVersion),
  );

  function signalEventsModified(): void {
    set(eventsVersion, get(eventsVersion) + 1);
  }

  function acknowledgeModifications(): void {
    set(acknowledgedVersion, get(eventsVersion));
  }

  function setAssociatedLocations(data: string[]): void {
    set(associatedLocations, data);
  }

  function setLocationLabels(data: LocationLabel[]): void {
    set(locationLabels, data);
  }

  function setTransactionStatusSummary(data: TransactionStatus): void {
    set(transactionStatusSummary, data);
  }

  return {
    acknowledgeModifications,
    associatedLocations,
    eventsVersion,
    hasUnprocessedModifications,
    locationLabels,
    setAssociatedLocations,
    setLocationLabels,
    setTransactionStatusSummary,
    signalEventsModified,
    transactionStatusSummary,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoryStore, import.meta.hot));
