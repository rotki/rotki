import { type Section, Status } from '@/types/status';

export const useStatusUpdater = (section: Section, ignore = false) => {
  const { setStatus, getStatus, isLoading } = useStatusStore();
  const updateStatus = (status: Status, otherSection?: Section) => {
    if (ignore) {
      return;
    }
    setStatus({
      section: otherSection ?? section,
      status
    });
  };

  const resetStatus = (otherSection?: Section) => {
    setStatus({
      section: otherSection ?? section,
      status: Status.NONE
    });
  };

  const loading = (otherSection?: Section) =>
    get(isLoading(otherSection ?? section));

  const isFirstLoad = (otherSection?: Section) =>
    get(getStatus(otherSection ?? section)) === Status.NONE;

  const fetchDisabled = (refresh: boolean, otherSection?: Section) => {
    return !(isFirstLoad(otherSection) || refresh) || loading(otherSection);
  };

  const getSectionStatus = (otherSection?: Section) => {
    return get(getStatus(otherSection ?? section));
  };

  return {
    loading,
    isFirstLoad,
    setStatus: updateStatus,
    getStatus: getSectionStatus,
    fetchDisabled,
    resetStatus
  };
};
