import { AaveBalances, AaveHistory, type ProfitLossModel } from '@rotki/common';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';
import { getProtocolAddresses } from '@/utils/addresses';
import { isTaskCancelled } from '@/utils';
import { balanceSum } from '@/utils/calculation';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { useAaveApi } from '@/composables/api/defi/aave';
import { useStatusUpdater } from '@/composables/status';
import { usePremium } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import type { TaskMeta } from '@/types/task';

export const useAaveStore = defineStore('defi/aave', () => {
  const balances = ref<AaveBalances>({});
  const history = ref<AaveHistory>({});

  const { notify } = useNotificationsStore();
  const { awaitTask } = useTaskStore();
  const { activeModules } = useModules();
  const premium = usePremium();
  const { t } = useI18n();

  const { fetchAaveBalances, fetchAaveHistory } = useAaveApi();

  const { fetchDisabled, resetStatus, setStatus } = useStatusUpdater(Section.DEFI_AAVE_BALANCES);

  const aaveTotalEarned = (addresses: string[]): ComputedRef<ProfitLossModel[]> => computed<ProfitLossModel[]>(() => {
    const earned: ProfitLossModel[] = [];
    const aaveHistory = get(history);

    for (const address in aaveHistory) {
      if (addresses.length > 0 && !addresses.includes(address))
        continue;

      const totalEarned = aaveHistory[address].totalEarnedInterest;
      for (const asset in totalEarned) {
        const index = earned.findIndex(e => e.asset === asset);
        if (index < 0) {
          earned.push({
            address: '',
            asset,
            value: totalEarned[asset],
          });
        }
        else {
          earned[index] = {
            ...earned[index],
            value: balanceSum(earned[index].value, totalEarned[asset]),
          };
        }
      }
    }
    return earned;
  });

  const fetchBalances = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.AAVE))
      return;

    if (fetchDisabled(refresh))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);

    try {
      const taskType = TaskType.AAVE_BALANCES;
      const { taskId } = await fetchAaveBalances();
      const { result } = await awaitTask<AaveBalances, TaskMeta>(taskId, taskType, {
        title: t('actions.defi.aave_balances.task.title'),
      });
      set(balances, AaveBalances.parse(result));
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        const message = t('actions.defi.aave_balances.error.description', {
          error: error.message,
        });
        const title = t('actions.defi.aave_balances.error.title');
        notify({
          display: true,
          message,
          title,
        });
      }
    }

    setStatus(Status.LOADED);
  };

  const fetchHistory = async (payload: { refresh?: boolean }): Promise<void> => {
    if (!get(activeModules).includes(Module.AAVE) || !get(premium))
      return;

    const section = { section: Section.DEFI_AAVE_HISTORY };
    const refresh = payload?.refresh;

    if (fetchDisabled(!!refresh, section))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const taskType = TaskType.AAVE_HISTORY;
      const { taskId } = await fetchAaveHistory();
      const { result } = await awaitTask<AaveHistory, TaskMeta>(taskId, taskType, {
        title: t('actions.defi.aave_history.task.title'),
      });

      set(history, AaveHistory.parse(result));
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        const message = t('actions.defi.aave_history.error.description', {
          error: error.message,
        });
        const title = t('actions.defi.aave_history.error.title');

        notify({
          display: true,
          message,
          title,
        });
      }
    }

    setStatus(Status.LOADED, section);
  };

  const reset = (): void => {
    set(balances, {});
    set(history, {});
    resetStatus();
    resetStatus({ section: Section.DEFI_AAVE_HISTORY });
  };

  const addresses = computed<string[]>(() => getProtocolAddresses(get(balances), get(history)));

  return {
    aaveTotalEarned,
    addresses,
    balances,
    fetchBalances,
    fetchHistory,
    history,
    reset,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAaveStore, import.meta.hot));
