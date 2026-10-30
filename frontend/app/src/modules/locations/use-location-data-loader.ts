import { startPromise } from '@shared/utils';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useHistoryApi } from '@/modules/history/api/use-history-api';
import { flatLocationTree } from '@/modules/locations/flat-location-tree';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

interface UseLocationDataLoaderReturn {
  /** Starts loading the location details and the location tree. */
  loadLocations: () => void;
}

/** Loads what a session needs to know about locations, without waiting for it. */
export function useLocationDataLoader(): UseLocationDataLoaderReturn {
  const { allLocations } = storeToRefs(useLocationStore());
  const { setNodes } = useLocationTreeStore();
  const { fetchAllLocations } = useHistoryApi();

  const loadLocations = (): void => {
    startPromise(fetchAllLocations().then(({ locations }) => {
      set(allLocations, locations);
      setNodes(flatLocationTree(locations));
    }));
  };

  return { loadLocations };
}
