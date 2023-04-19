import { Section, Status } from '@/types/status';

export const useDataLoader = () => {
  const { shouldFetchData } = storeToRefs(useSessionAuthStore());
  const { fetchWatchers } = useWatchersStore();
  const { fetchTags } = useTagStore();
  const { fetchIgnoredAssets } = useIgnoredAssetsStore();
  const { fetchNetValue } = useStatisticsStore();

  const { fetch, refreshPrices } = useBalances();

  const refreshData = async (): Promise<void> => {
    logger.info('Refreshing data');

    await Promise.allSettled([
      fetchIgnoredAssets(),
      fetchWatchers(),
      fetch(),
      fetchNetValue()
    ]);
    await refreshPrices();
  };

  const load = async (): Promise<void> => {
    await fetchTags();

    if (get(shouldFetchData)) {
      startPromise(refreshData());
    } else {
      const ethUpdater = useStatusUpdater(Section.BLOCKCHAIN_ETH);
      const btcUpdater = useStatusUpdater(Section.BLOCKCHAIN_BTC);
      ethUpdater.setStatus(Status.LOADED);
      btcUpdater.setStatus(Status.LOADED);
    }
  };

  return {
    load
  };
};
