import { useLocationTreeApi } from '@/modules/locations/use-location-tree-api';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

interface UseLocationTreeReturn {
  refreshLocationTree: () => Promise<void>;
}

/** Loads the location tree into {@link useLocationTreeStore}. */
export function useLocationTree(): UseLocationTreeReturn {
  const { fetchLocationTree } = useLocationTreeApi();
  const store = useLocationTreeStore();

  const refreshLocationTree = async (): Promise<void> => {
    store.setNodes(await fetchLocationTree());
  };

  return { refreshLocationTree };
}
