import { type Section, Status } from '@/types/status';

interface Opts {
  section?: Section;
  subsection?: string;
}

export function useStatusUpdater(defaultSection: Section) {
  const { setStatus, getStatus, isLoading } = useStatusStore();
  const updateStatus = (status: Status, opts: Opts = {}) => {
    const { section = defaultSection, subsection } = opts;

    setStatus({
      section,
      subsection,
      status,
    });
  };

  const resetStatus = (opts: Opts = {}) => {
    const { section = defaultSection, subsection } = opts;

    setStatus({
      section,
      subsection,
      status: Status.NONE,
    });
  };

  const loading = (opts: Opts = {}) => {
    const { section = defaultSection, subsection } = opts;
    return get(isLoading(section, subsection));
  };

  const isFirstLoad = (opts: Opts = {}) => {
    const { section = defaultSection, subsection } = opts;
    return get(getStatus(section, subsection)) === Status.NONE;
  };

  const fetchDisabled = (refresh: boolean, opts: Opts = {}) => !(isFirstLoad(opts) || refresh) || loading(opts);

  const getSectionStatus = (opts: Opts = {}) => {
    const { section = defaultSection, subsection } = opts;
    return get(getStatus(section, subsection));
  };

  return {
    loading,
    isFirstLoad,
    setStatus: updateStatus,
    getStatus: getSectionStatus,
    fetchDisabled,
    resetStatus,
  };
}
