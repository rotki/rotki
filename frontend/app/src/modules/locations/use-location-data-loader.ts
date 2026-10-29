import { startPromise } from '@shared/utils';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useHistoryApi } from '@/modules/history/api/use-history-api';
import { useLocationTree } from '@/modules/locations/use-location-tree';

interface UseLocationDataLoaderReturn {
  /** Starts loading the location details, the exchange connectors and the location tree. */
  loadLocations: () => void;
}

/** Loads what a session needs to know about locations, without waiting for it. */
export function useLocationDataLoader(): UseLocationDataLoaderReturn {
  const { allLocations, exchangeConnectors } = storeToRefs(useLocationStore());
  const { fetchAllLocations } = useHistoryApi();
  const { getSupportedExchanges } = useExchangeApi();
  const { refreshLocationTree } = useLocationTree();

  const loadLocations = (): void => {
    startPromise(fetchAllLocations().then(({ locations }) => {
      set(allLocations, locations);
    }));
    startPromise(refreshLocationTree());
    startPromise(getSupportedExchanges().then((connectors) => {
      set(exchangeConnectors, connectors);
    }));
  };

  return { loadLocations };
}
