import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { Section, Status } from '@/modules/common/status';
import { useStatusStore } from '@/store/status';

export { Section, Status };

interface UseSectionStatusReturn {
  isInitialLoading: ComputedRef<boolean>;
  isLoading: ComputedRef<boolean>;
}

export function useSectionStatus(
  section: MaybeRefOrGetter<Section>,
  subsection?: MaybeRefOrGetter<string>,
): UseSectionStatusReturn {
  const { useIsLoading, useShouldShowLoadingScreen } = useStatusStore();
  return {
    isInitialLoading: useShouldShowLoadingScreen(section, subsection),
    isLoading: useIsLoading(section, subsection),
  };
}

export async function waitUntilIdle(section: Section, subsection?: string): Promise<void> {
  const { getIsLoading } = useStatusStore();
  if (getIsLoading(section, subsection))
    await until(() => getIsLoading(section, subsection)).toBe(false);
}

interface Opts {
  section?: Section;
  subsection?: string;
}

interface UseStatusUpdaterReturn {
  loading: (opts?: Opts) => boolean;
  isFirstLoad: (opts?: Opts) => boolean;
  setStatus: (status: Status, opts?: Opts) => void;
  getStatus: (opts?: Opts) => Status;
  fetchDisabled: (refresh: boolean, opts?: Opts) => boolean;
  resetStatus: (opts?: Opts) => void;
}

export function useStatusUpdater(defaultSection: Section): UseStatusUpdaterReturn {
  const { getIsLoading, getStatus, setStatus } = useStatusStore();
  const updateStatus = (status: Status, opts: Opts = {}): void => {
    const { section = defaultSection, subsection } = opts;

    setStatus({
      section,
      status,
      subsection,
    });
  };

  const resetStatus = (opts: Opts = {}): void => {
    const { section = defaultSection, subsection } = opts;

    setStatus({
      section,
      status: Status.NONE,
      subsection,
    });
  };

  const loading = (opts: Opts = {}): boolean => {
    const { section = defaultSection, subsection } = opts;
    return getIsLoading(section, subsection);
  };

  const isFirstLoad = (opts: Opts = {}): boolean => {
    const { section = defaultSection, subsection } = opts;
    return getStatus(section, subsection) === Status.NONE;
  };

  const fetchDisabled = (refresh: boolean, opts: Opts = {}): boolean => !(isFirstLoad(opts) || refresh) || loading(opts);

  const getSectionStatus = (opts: Opts = {}): Status => {
    const { section = defaultSection, subsection } = opts;
    return getStatus(section, subsection);
  };

  return {
    fetchDisabled,
    getStatus: getSectionStatus,
    isFirstLoad,
    loading,
    resetStatus,
    setStatus: updateStatus,
  };
}
