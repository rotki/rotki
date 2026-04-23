import type { MaybeRefOrGetter } from 'vue';
import type { StatusPayload } from '@/modules/core/common/action';
import { isEmpty } from 'es-toolkit/compat';
import { Section, Status } from '@/modules/core/common/status';

type SectionStatus = Record<string, Status>;

type StatusState = Partial<Record<Section, SectionStatus>>;

const defaultSection = 'default';

// Balance sections no longer write REFRESHING (refresh activity lives in useBalanceRefreshState);
// this fallthrough keeps behavior correct for history/staking/nft/liquity which still use it.
function isInitialLoadingStatus(status: Status): boolean {
  return status !== Status.LOADED && status !== Status.PARTIALLY_LOADED && status !== Status.REFRESHING;
}

function isLoadingStatus(status: Status): boolean {
  return status === Status.LOADING || status === Status.PARTIALLY_LOADED || status === Status.REFRESHING;
}

function matchesStatus(statuses: SectionStatus, subsection: string, fn: (status: Status) => boolean): boolean {
  const subsectionStatus = statuses[subsection];
  if (subsection === defaultSection)
    return !subsectionStatus && !isEmpty(statuses) ? Object.values(statuses).some(fn) : fn(subsectionStatus);
  else return subsectionStatus ? fn(subsectionStatus) : false;
}

export const useStatusStore = defineStore('status', () => {
  const status = ref<StatusState>({});

  const resetStatus = (section: Section, subsection: string = defaultSection): void => {
    const statuses = { ...get(status) };
    delete statuses[section]?.[subsection];
    if (isEmpty(statuses[section]))
      delete statuses[section];
    set(status, statuses);
  };

  const setStatus = ({ section, status: newStatus, subsection = defaultSection }: StatusPayload): void => {
    const statuses = get(status);
    const sectionStatus = statuses[section] ?? { [defaultSection]: Status.NONE };

    if (sectionStatus[subsection] === newStatus)
      return;

    if (newStatus === Status.NONE) {
      resetStatus(section, subsection);
    }
    else {
      set(status, {
        ...statuses,
        [section]: {
          ...statuses[section],
          [subsection]: newStatus,
        },
      });
    }
  };

  const getStatus = (section: Section, subsection: string = defaultSection): Status =>
    get(status)[section]?.[subsection] ?? Status.NONE;

  const getIsLoading = (
    section: Section,
    subsection: string = defaultSection,
  ): boolean => {
    const statuses = get(status)[section];
    if (!statuses)
      return false;

    return matchesStatus(statuses, subsection, isLoadingStatus);
  };

  const useIsLoading = (
    section: MaybeRefOrGetter<Section>,
    subsection: MaybeRefOrGetter<string> = defaultSection,
  ): ComputedRef<boolean> => computed<boolean>(() => getIsLoading(toValue(section), toValue(subsection)));

  const getIsInitialLoading = (
    section: Section,
    subsection: string = defaultSection,
  ): boolean => {
    const statuses = get(status)[section];
    if (!statuses)
      return true;

    return matchesStatus(statuses, subsection, isInitialLoadingStatus);
  };

  const useShouldShowLoadingScreen = (
    section: MaybeRefOrGetter<Section>,
    subsection: MaybeRefOrGetter<string> = defaultSection,
  ): ComputedRef<boolean> => computed<boolean>(() => getIsInitialLoading(toValue(section), toValue(subsection)));

  const detailsLoading = logicOr(
    useIsLoading(Section.BLOCKCHAIN),
    useIsLoading(Section.EXCHANGES),
    useIsLoading(Section.MANUAL_BALANCES),
  );

  return {
    detailsLoading,
    getIsInitialLoading,
    getIsLoading,
    getStatus,
    resetStatus,
    setStatus,
    useShouldShowLoadingScreen,
    useIsLoading,
    status,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useStatusStore, import.meta.hot));
