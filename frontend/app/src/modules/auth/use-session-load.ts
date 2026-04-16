import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useWhitelistedAssetOperations } from '@/modules/assets/use-whitelisted-asset-operations';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useBalanceFetching } from '@/modules/balances/use-balance-fetching';
import { logger } from '@/modules/core/common/logging/logging';
import { Section, Status } from '@/modules/core/common/status';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { sigilBus } from '@/modules/core/sigil/event-bus';
import { useHistoryApi } from '@/modules/history/api/use-history-api';
import { useSchedulerState } from '@/modules/session/use-scheduler-state';
import { useStatusUpdater } from '@/modules/shell/sync-progress/use-status-updater';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { useTagOperations } from '@/modules/tags/use-tag-operations';

const isAutoFetchDisabled = import.meta.env.VITE_NO_AUTO_FETCH === 'true';

interface UseDataLoaderReturn { load: () => void }

export function useDataLoader(): UseDataLoaderReturn {
  const { shouldFetchData } = storeToRefs(useSessionAuthStore());
  const { fetchTags } = useTagOperations();
  const { fetchIgnoredAssets } = useIgnoredAssetOperations();
  const { fetchWhitelistedAssets } = useWhitelistedAssetOperations();
  const { fetchNetValue } = useStatisticsDataFetching();
  const { allLocations } = storeToRefs(useLocationStore());
  const { fetchAllLocations } = useHistoryApi();
  const { fetch } = useBalanceFetching();
  const { refreshPrices } = usePriceRefresh();
  const { setStatus } = useStatusUpdater(Section.BLOCKCHAIN);

  const { onBalancesLoaded } = useSchedulerState();

  const refreshData = async (): Promise<void> => {
    logger.info('Refreshing data');

    await Promise.allSettled([
      fetchIgnoredAssets(),
      fetchWhitelistedAssets(),
      fetch(),
      fetchNetValue(),
    ]);
    await refreshPrices();
    onBalancesLoaded();
    sigilBus.emit('balances:loaded');
  };

  const load = (): void => {
    startPromise(fetchTags());
    startPromise(fetchAllLocations().then(({ locations }) => {
      set(allLocations, locations);
    }));

    if (isAutoFetchDisabled) {
      logger.warn('Auto-fetch disabled by VITE_NO_AUTO_FETCH');
      setStatus(Status.LOADED, { subsection: Blockchain.ETH });
      setStatus(Status.LOADED, { subsection: Blockchain.BTC });
    }
    else if (get(shouldFetchData)) {
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
