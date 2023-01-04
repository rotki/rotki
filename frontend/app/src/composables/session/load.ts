import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useBalancesStore } from '@/store/balances';
import { useTransactions } from '@/store/history/transactions';
import { useSessionAuthStore } from '@/store/session/auth';
import { useTagStore } from '@/store/session/tags';
import { useWatchersStore } from '@/store/session/watchers';
import { useStatisticsStore } from '@/store/statistics';
import { Section, Status } from '@/types/status';
import { startPromise } from '@/utils';
import { logger } from '@/utils/logging';

export const useDataLoader = () => {
  const { shouldFetchData } = storeToRefs(useSessionAuthStore());
  const { fetchWatchers } = useWatchersStore();
  const { fetchTags } = useTagStore();
  const { fetchIgnoredAssets } = useIgnoredAssetsStore();
  const { fetchNetValue } = useStatisticsStore();
  const { fetchCounterparties } = useTransactions();
  const { fetch, refreshPrices } = useBalancesStore();

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
    await fetchCounterparties();

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
