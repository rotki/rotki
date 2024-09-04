import { Blockchain } from '@rotki/common';
import { Section, Status } from '@/types/status';

interface UseDataLoaderReturn { load: () => void }

export function useDataLoader(): UseDataLoaderReturn {
  const { shouldFetchData } = storeToRefs(useSessionAuthStore());
  const { fetchWatchers } = useWatchersStore();
  const { fetchTags } = useTagStore();
  const { fetchIgnoredAssets } = useIgnoredAssetsStore();
  const { fetchWhitelistedAssets } = useWhitelistedAssetsStore();
  const { fetchNetValue } = useStatisticsStore();
  const { fetchAllTradeLocations } = useLocationStore();
  const { fetch, refreshPrices } = useBalances();
  const { setStatus } = useStatusUpdater(Section.BLOCKCHAIN);

  const refreshData = async (): Promise<void> => {
    logger.info('Refreshing data');

    await Promise.allSettled([
      fetchIgnoredAssets(),
      fetchWhitelistedAssets(),
      fetchWatchers(),
      fetch(),
      fetchNetValue(),
    ]);
    await refreshPrices();
  };

  const load = (): void => {
    startPromise(fetchTags());
    startPromise(fetchAllTradeLocations());

    if (get(shouldFetchData)) {
      startPromise(refreshData());
    }
    else {
      setStatus(Status.LOADED, { subsection: Blockchain.ETH });
      setStatus(Status.LOADED, { subsection: Blockchain.BTC });
    }
  };

  return {
    load,
  };
}
