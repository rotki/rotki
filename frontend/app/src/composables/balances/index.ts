import type { AllBalancePayload } from '@/types/blockchain/accounts';
import { startPromise } from '@shared/utils';
import { useBalancesApi } from '@/composables/api/balances';
import { useBlockchains } from '@/composables/blockchain';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { usePriceRefresh } from '@/modules/prices/use-price-refresh';
import { usePriceTaskManager } from '@/modules/prices/use-price-task-manager';
import { useStatisticsStore } from '@/store/statistics';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';

export const useBalances = createSharedComposable(() => {
  const { fetchManualBalances } = useManualBalances();
  const { fetchConnectedExchangeBalances } = useExchanges();
  const { refreshAccounts } = useBlockchains();
  const { queryBalancesAsync } = useBalancesApi();
  const { fetchExchangeRates } = usePriceTaskManager();
  const { refreshPrices } = usePriceRefresh();
  const { notifyError } = useNotifications();
  const { awaitTask, isTaskRunning } = useTaskStore();
  const { t } = useI18n({ useScope: 'global' });
  const { fetchNetValue } = useStatisticsStore();

  const fetchBalances = async (payload: Partial<AllBalancePayload> = {}): Promise<void> => {
    const taskType = TaskType.QUERY_BALANCES;
    if (isTaskRunning(taskType))
      return;

    try {
      const { taskId } = await queryBalancesAsync(payload);
      await awaitTask(taskId, taskType, {
        title: t('actions.balances.all_balances.task.title'),
      });
    }
    catch (error: unknown) {
      if (!isTaskCancelled(error)) {
        notifyError(
          t('actions.balances.all_balances.error.title'),
          t('actions.balances.all_balances.error.message', {
            message: getErrorMessage(error),
          }),
        );
      }
    }
  };

  const fetch = async (): Promise<void> => {
    await fetchExchangeRates();
    await Promise.allSettled([fetchManualBalances(), refreshAccounts(), fetchConnectedExchangeBalances()]);
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
