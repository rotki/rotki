import { type MaybeRef } from '@vueuse/core';
import { type ComputedRef } from 'vue';
import { Section, Status, defiSections } from '@/types/status';
import { type StatusPayload } from '@/types/action';

const isLoading = (status: MaybeRef<Status>): boolean =>
  get(status) === Status.LOADING ||
  get(status) === Status.PARTIALLY_LOADED ||
  get(status) === Status.REFRESHING;

export const useStatusStore = defineStore('status', () => {
  const status = ref<Partial<Record<Section, Status>>>({});

  const detailsLoading = computed(() => {
    return (
      isLoading(getStatus(Section.BLOCKCHAIN_ETH)) ||
      isLoading(getStatus(Section.BLOCKCHAIN_BTC)) ||
      isLoading(getStatus(Section.BLOCKCHAIN_KSM)) ||
      isLoading(getStatus(Section.BLOCKCHAIN_AVAX)) ||
      isLoading(getStatus(Section.EXCHANGES)) ||
      isLoading(getStatus(Section.MANUAL_BALANCES))
    );
  });

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
    computed<Status>(() => {
      return get(status)[section] ?? Status.NONE;
    });

  return {
    status,
    detailsLoading,
    isLoading,
    resetDefiStatus,
    setStatus,
    getStatus
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useStatusStore, import.meta.hot));
}

/**
 * Gets section status
 *
 * @deprecated use useStatusUpdater instead
 * @param section
 */
export const getStatus = (section: Section): Status => {
  const { getStatus } = useStatusStore();
  return get(getStatus(section));
};

/**
 * Sets section status
 *
 * @deprecated use useStatusUpdater instead
 * @param newStatus
 * @param section
 */
export const setStatus: (newStatus: Status, section: Section) => void = (
  newStatus,
  section
) => {
  const { getStatus, setStatus } = useStatusStore();
  if (get(getStatus(section)) === newStatus) {
    return;
  }
  setStatus({
    section,
    status: newStatus
  });
};
