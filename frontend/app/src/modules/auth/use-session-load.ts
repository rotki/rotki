import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useAccountLoadState } from '@/modules/accounts/use-account-load-state';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { usePriceSeed } from '@/modules/assets/prices/use-price-seed';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useWhitelistedAssetOperations } from '@/modules/assets/use-whitelisted-asset-operations';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useBalanceFetching } from '@/modules/balances/use-balance-fetching';
import { logger } from '@/modules/core/common/logging/logging';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { sigilBus } from '@/modules/core/sigil/event-bus';
import { useHistoryApi } from '@/modules/history/api/use-history-api';
import { useSchedulerState } from '@/modules/session/use-scheduler-state';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { useTagOperations } from '@/modules/tags/use-tag-operations';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

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
  const { fetchCached, refreshFromChain } = useBalanceFetching();
  const { refreshPrices } = usePriceRefresh();
  const { seedFromHistoric } = usePriceSeed();
  const { markCompleted } = useTaskOrchestrator();
  const { arm: armAccountLoad, release: releaseAccountLoad } = useAccountLoadState();

  /**
   * Nothing is fetched on this path: the balances are already in the DB and were restored with the
   * session. The ledger has to be told so, or every reader would treat a restored session as
   * "never loaded" and show a loading screen over data that is right there.
   */
  const markRestored = (): void => {
    markCompleted(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.ETH);
    markCompleted(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.BTC);
  };

  const { onBalancesLoaded } = useSchedulerState();

  const refreshData = async (): Promise<void> => {
    logger.info('Refreshing data');

    // The ignored/whitelisted lists decide which assets are counted towards the totals, so
    // they have to be in place before the balances land. Fetching them alongside the balances
    // makes the net worth briefly include the ignored assets, until the lists arrive.
    // https://github.com/rotki/rotki/issues/12764
    await Promise.allSettled([
      fetchIgnoredAssets(),
      fetchWhitelistedAssets(),
    ]);
    try {
      await Promise.allSettled([
        fetchCached(),
        fetchNetValue(),
      ]);
    }
    finally {
      // The bound on the account gate. `fetchAccounts` normally opens it much earlier, the moment
      // its read settles; this is the guarantee for the case where the read never happens at all,
      // so a waiter cannot outlive the load that was supposed to satisfy it.
      releaseAccountLoad();
    }
    await seedFromHistoric();
    startPromise(refreshPrices());
    startPromise(refreshFromChain());
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
      markRestored();
    }
    else if (get(shouldFetchData)) {
      // Armed here, synchronously, rather than inside the read. `refreshData` awaits the
      // ignored/whitelisted lists and then the exchange rates before it ever reaches the accounts,
      // and a consumer that snapshots the store during that stretch sees it empty. Navigating
      // straight into history is fast enough to land there, which is why the sync could report
      // complete over a scope of nothing.
      armAccountLoad();
      startPromise(refreshData());
    }
    else {
      markRestored();
    }
  };

  return {
    load,
  };
}
