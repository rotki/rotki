import { createSharedComposable } from '@vueuse/core';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { useAutoTokenDetection } from '@/modules/balances/blockchain/use-auto-token-detection';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { RefreshMode } from '@/modules/balances/types/refresh-mode';
import { useAllBalancesQuery } from '@/modules/balances/use-all-balances-query';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useSnapshotSchedule } from '@/modules/balances/use-snapshot-schedule';
import { useBanks } from '@/modules/banks/use-banks';
import { logger } from '@/modules/core/common/logging/logging';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';

export const useBalanceFetching = createSharedComposable(() => {
  const { fetchManualBalances } = useManualBalances();
  const { fetchConnectedExchangeBalances } = useExchanges();
  const { fetchBankBalances, refreshBankConnections } = useBanks();

  /** Banks are listed before they are queried: the balance query is a no-op without connections. */
  const fetchBanks = async (): Promise<void> => {
    await refreshBankConnections();
    await fetchBankBalances();
  };
  const { fetchAccounts } = useBlockchainAccountManagement();
  const { fetchExchangeRates } = usePriceTaskManager();
  const { refreshPrices } = usePriceRefresh();
  const { fetchNetValue } = useStatisticsDataFetching();
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const { skipReason: autoDetectSkipReason, withDetection } = useAutoTokenDetection();
  const { isSnapshotDue } = useSnapshotSchedule();
  const { fetchBalances, queueSnapshot } = useAllBalancesQuery();

  /**
   * ⭐ `fetchAccounts`, not `refreshAccounts`. Passing no chain made the latter an accounts read and
   * nothing else — both halves of its balance decision need one — so the name promised work it
   * never did here. Each chain's hydration still happens inside the walk, as its accounts land.
   */
  const fetchCached = async (): Promise<void> => {
    await fetchExchangeRates();
    await Promise.allSettled([fetchManualBalances(), fetchAccounts({ refreshEns: true }), fetchConnectedExchangeBalances(), fetchBanks()]);
  };

  /**
   * The login load: every chain, then the day's snapshot if the schedule is due.
   *
   * The schedule is read before the batch, so a login with no snapshot due declares no snapshot
   * node at all. Forcing a save is {@link fetchBalances} from `forceSave`.
   */
  const refreshFromChain = async (): Promise<void> => withDetection(async (detect) => {
    logger.debug(detect
      ? 'refreshFromChain: detect-then-query, every chain'
      : `refreshFromChain: query only (${autoDetectSkipReason() ?? 'unknown'}), every chain`);

    const due = await isSnapshotDue();
    if (!due)
      logger.debug('refreshFromChain: snapshot not due, no aggregate query');

    await refreshBlockchainBalances({}, RefreshMode.BACKGROUND, {
      detect,
      followUp: due ? queueSnapshot : undefined,
    });
  });

  /**
   * §6's periodic flow: every chain, entering at the job, no detection.
   *
   * 🔴 The tick never asked a chain anything. It passed `{ periodic: true }` to `refreshAccounts`,
   * whose no-chain branch is a *cached* read — the DB, not the network — so "Automatic balance
   * refresh" re-read balances the backend had already written on its own schedule and never
   * triggered a query itself. The `periodic` refresh mode, the one that settles SKIPPED on a busy
   * chain rather than joining it, had no caller that could reach it at all.
   *
   * ⚠️ This does now cost network calls on a timer, which is why it belongs behind a setting the
   * user turns on: `refreshPeriod` defaults to `-1` and the scheduler only starts when it is
   * positive. A chain still mid-refresh is skipped rather than queued, so ticks cannot pile up.
   */
  const autoRefresh = async (): Promise<void> => {
    await Promise.allSettled([
      fetchManualBalances(),
      fetchAccounts({ refreshEns: true }),
      fetchConnectedExchangeBalances(),
      fetchBanks(),
      fetchNetValue(),
    ]);

    await Promise.allSettled([
      refreshBlockchainBalances({}, RefreshMode.PERIODIC),
      refreshPrices(true),
    ]);
  };

  return {
    autoRefresh,
    fetchBalances,
    fetchCached,
    refreshFromChain,
  };
});
