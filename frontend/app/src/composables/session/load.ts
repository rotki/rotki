import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useHistoryApi } from '@/composables/api/history';
import { useSchedulerState } from '@/composables/session/use-scheduler-state';
import { useStatusUpdater } from '@/composables/status';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useWhitelistedAssetOperations } from '@/modules/assets/use-whitelisted-asset-operations';
import { useBalanceFetching } from '@/modules/balances/use-balance-fetching';
import { logger } from '@/modules/common/logging/logging';
import { Section, Status } from '@/modules/common/status';
import { useLocationStore } from '@/modules/common/use-location-store';
import { usePriceRefresh } from '@/modules/prices/use-price-refresh';
import { useSessionAuthStore } from '@/modules/session/use-session-auth-store';
import { useTagOperations } from '@/modules/session/use-tag-operations';
import { sigilBus } from '@/modules/sigil/event-bus';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';

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
