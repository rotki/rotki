import { Section, Status, defiSections } from '@/types/status';
import { type StatusPayload } from '@/types/action';

export const useStatusStore = defineStore('status', () => {
  const status = ref<Partial<Record<Section, Status>>>({});

  const resetDefiStatus = (): void => {
    const newStatus = Status.NONE;
    defiSections.forEach(section => {
      status.value[section] = newStatus;
    });
  };

  const setStatus = ({ section, status: newStatus }: StatusPayload): void => {
    const statuses = get(status);
    if (statuses[section] === newStatus) {
      return;
    }
    set(status, { ...statuses, [section]: newStatus });
  };

  const getStatus = (section: Section): ComputedRef<Status> =>
    computed<Status>(() => get(status)[section] ?? Status.NONE);

  const isLoading = (section: Section): ComputedRef<boolean> =>
    computed(() => {
      const status = get(getStatus(section));
      return (
        status === Status.LOADING ||
        status === Status.PARTIALLY_LOADED ||
        status === Status.REFRESHING
      );
    });

  const shouldShowLoadingScreen = (section: Section): ComputedRef<boolean> =>
    computed(() => {
      const status = get(getStatus(section));
      return (
        status !== Status.LOADED &&
        status !== Status.PARTIALLY_LOADED &&
        status !== Status.REFRESHING
      );
    });

  const detailsLoading = logicOr(
    isLoading(Section.BLOCKCHAIN_ETH),
    isLoading(Section.BLOCKCHAIN_BTC),
    isLoading(Section.BLOCKCHAIN_KSM),
    isLoading(Section.BLOCKCHAIN_AVAX),
    isLoading(Section.EXCHANGES),
    isLoading(Section.MANUAL_BALANCES)
  );

  return {
    status,
    detailsLoading,
    isLoading,
    shouldShowLoadingScreen,
    resetDefiStatus,
    setStatus,
    getStatus
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useStatusStore, import.meta.hot));
}
