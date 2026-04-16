import type { AllBalancePayload } from '@/modules/accounts/blockchain-accounts';
import { startPromise } from '@shared/utils';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { useBalancesApi } from '@/modules/balances/api/use-balances-api';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
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

  const fetch = async (): Promise<void> => {
    await fetchExchangeRates();
    await Promise.allSettled([fetchManualBalances(), refreshAccounts(), fetchConnectedExchangeBalances()]);

    startPromise(refreshBlockchainBalances());
    startPromise(fetchBalances());
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
  };
});
