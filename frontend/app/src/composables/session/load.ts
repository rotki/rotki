import { useBalances } from '@/composables/balances';
import { useStatusUpdater } from '@/composables/status';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useWhitelistedAssetsStore } from '@/store/assets/whitelisted';
import { useLocationStore } from '@/store/locations';
import { useSessionAuthStore } from '@/store/session/auth';
import { useTagStore } from '@/store/session/tags';
import { useStatisticsStore } from '@/store/statistics';
import { Section, Status } from '@/types/status';
import { logger } from '@/utils/logging';
import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';

interface UseDataLoaderReturn { load: () => void }

export function useDataLoader(): UseDataLoaderReturn {
  const { shouldFetchData } = storeToRefs(useSessionAuthStore());
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
