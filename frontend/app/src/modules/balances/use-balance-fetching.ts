import type { AllBalancePayload } from '@/modules/accounts/blockchain-accounts';
import { startPromise } from '@shared/utils';
import { map as mapResult, type Result } from 'plainfp/result';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { useBalancesApi } from '@/modules/balances/api/use-balances-api';
import { useAutoTokenDetection } from '@/modules/balances/blockchain/use-auto-token-detection';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

export const useBalanceFetching = createSharedComposable(() => {
  const { fetchManualBalances } = useManualBalances();
  const { fetchConnectedExchangeBalances } = useExchanges();
  const { refreshAccounts } = useBlockchainAccountManagement();
  const { queryBalancesAsync } = useBalancesApi();
  const { fetchExchangeRates } = usePriceTaskManager();
  const { refreshPrices } = usePriceRefresh();
  const { notifyError } = useNotifications();
  const { submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });
  const { fetchNetValue } = useStatisticsDataFetching();
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const { maybeDetect: maybeAutoDetectTokens, skipReason: autoDetectSkipReason, willDetect } = useAutoTokenDetection();
  const { supportedChains, txEvmChains } = useSupportedChains();

  function getNonEvmTxChains(): string[] {
    const evmIds = new Set(get(txEvmChains).map(c => c.id));
    return get(supportedChains)
      .map(c => c.id)
      .filter(id => !evmIds.has(id));
  }

  const fetchBalances = async (payload: Partial<AllBalancePayload> = {}): Promise<void> => {
    const description = payload.ignoreErrors
      ? `${t('actions.balances.all_balances.task.description')} ${t('actions.balances.all_balances.task.ignore_errors_note')}`
      : t('actions.balances.all_balances.task.description');

    // Singleton all-balances snapshot query; liveness is read off the orchestrator.
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.ALL_BALANCES),
      kind: ActivityKind.ALL_BALANCES,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask(async () => queryBalancesAsync(payload)),
        () => {},
      ),
      subtitle: description,
      title: t('task_center.group.all_balances'),
    });

    onActionableError(outcome, error => notifyError(
      t('actions.balances.all_balances.error.title'),
      t('actions.balances.all_balances.error.message', {
        message: error.message,
      }),
    ));
  };

  const fetchCached = async (): Promise<void> => {
    await fetchExchangeRates();
    await Promise.allSettled([fetchManualBalances(), refreshAccounts(), fetchConnectedExchangeBalances()]);
  };

  /**
   * ⭐ A refresh never snapshots. It used to end in `fetchBalances()` with an empty payload —
   * `GET /balances` reads the shared in-memory balances and persists on the backend's own
   * schedule, so a refresh was implicitly asking for a snapshot while its own per-chain queries
   * were still clearing and repopulating chains. That is how a 0-value row could reach the user's
   * net-worth history, and it forced the whole refresh to be ordered around it.
   *
   * Nothing is lost by dropping it: the backend takes automatic snapshots itself
   * (`tasks/manager.py::_maybe_update_snapshot_balances`, which checks `balance_save_frequency`,
   * runs `maybe_detect_new_tokens` first and passes `requested_save_data=True`). Explicit user
   * snapshots go through {@link fetchBalances} from `forceSave`, which is unchanged.
   *
   * ⚠️ The result of that call was discarded anyway (`mapResult(…, () => {})`) — it was only ever
   * made for the backend side effect, never for data this app reads.
   */
  const refreshFromChain = async (): Promise<void> => {
    if (willDetect()) {
      const nonEvmChains = getNonEvmTxChains();
      logger.debug(`refreshFromChain: detect-and-refresh-non-evm, non-EVM chains=[${nonEvmChains.join(', ')}]`);
      startPromise(maybeAutoDetectTokens());
      if (nonEvmChains.length > 0)
        await refreshBlockchainBalances({ blockchain: nonEvmChains });
    }
    else {
      logger.debug(`refreshFromChain: refresh-all-no-detection (${autoDetectSkipReason() ?? 'unknown'}), refreshing all chains`);
      await refreshBlockchainBalances();
    }
  };

  const fetch = async (): Promise<void> => {
    await fetchCached();
    startPromise(refreshFromChain());
  };

  const autoRefresh = async (): Promise<void> => {
    await Promise.allSettled([
      fetchManualBalances(),
      refreshAccounts({ periodic: true }),
      fetchConnectedExchangeBalances(),
      fetchNetValue(),
    ]);

    await refreshPrices(true);
  };

  return {
    autoRefresh,
    fetch,
    fetchBalances,
    fetchCached,
    refreshFromChain,
  };
});
