import type { AllBalancePayload } from '@/types/blockchain/accounts';
import { startPromise } from '@shared/utils';
import { useBalancesApi } from '@/composables/api/balances';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { usePriceRefresh } from '@/modules/prices/use-price-refresh';
import { usePriceTaskManager } from '@/modules/prices/use-price-task-manager';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';

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
