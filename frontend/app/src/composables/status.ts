import { useStatusStore } from '@/store/status';
import { Section, Status } from '@/types/status';

export const useStatusUpdater = (section: Section, ignore: boolean = false) => {
  const { setStatus, getStatus, isLoading } = useStatusStore();
  const updateStatus = (status: Status, otherSection?: Section) => {
    if (ignore) {
      return;
    }
    setStatus({
      section: otherSection ?? section,
      status: status
    });
  };

  const resetStatus = (otherSection?: Section) => {
    setStatus({
      section: otherSection ?? section,
      status: Status.NONE
    });
  };

  const loading = () => isLoading(getStatus(section));
  const isFirstLoad = () => get(getStatus(section)) === Status.NONE;
  const getSectionStatus = (otherSection?: Section) => {
    return get(getStatus(otherSection ?? section));
  };
  return {
    loading,
    isFirstLoad,
    setStatus: updateStatus,
    getStatus: getSectionStatus,
    resetStatus
  };
};
