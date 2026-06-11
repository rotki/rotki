import type { AllBalancePayload } from '@/modules/accounts/blockchain-accounts';
import { startPromise } from '@shared/utils';
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
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';

export const useBalanceFetching = createSharedComposable(() => {
  const { fetchManualBalances } = useManualBalances();
  const { fetchConnectedExchangeBalances } = useExchanges();
  const { refreshAccounts } = useBlockchainAccountManagement();
  const { queryBalancesAsync } = useBalancesApi();
  const { fetchExchangeRates } = usePriceTaskManager();
  const { refreshPrices } = usePriceRefresh();
  const { notifyError } = useNotifications();
  const { runTask } = useTaskHandler();
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
    const outcome = await runTask(
      async () => queryBalancesAsync(payload),
      { type: TaskType.QUERY_BALANCES, meta: { title: t('actions.balances.all_balances.task.title') } },
    );

    if (isActionableFailure(outcome)) {
      notifyError(
        t('actions.balances.all_balances.error.title'),
        t('actions.balances.all_balances.error.message', {
          message: outcome.message,
        }),
      );
    }
  };

  const fetchCached = async (): Promise<void> => {
    await fetchExchangeRates();
    await Promise.allSettled([fetchManualBalances(), refreshAccounts(), fetchConnectedExchangeBalances()]);
  };

  const refreshFromChain = async (): Promise<void> => {
    // Trigger the all-balances query only after the blockchain balances refresh
    // completes. GET /balances reads the shared in-memory balances and may persist
    // a snapshot; a per-chain refresh clears a chain's balances before repopulating
    // them, so running both concurrently can let the snapshot observe the transient
    // cleared state and save a 0-value snapshot while the balances recover right
    // after.
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
    await fetchBalances();
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
