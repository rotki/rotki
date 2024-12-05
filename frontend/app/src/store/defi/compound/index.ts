import { CompoundBalances, CompoundStats } from '@/types/defi/compound';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';
import { getProtocolAddresses } from '@/utils/addresses';
import { isTaskCancelled } from '@/utils';
import { toProfitLossModel } from '@/utils/defi';
import { useTaskStore } from '@/store/tasks';
import { useNotificationsStore } from '@/store/notifications';
import { useCompoundApi } from '@/composables/api/defi/compound';
import { useStatusUpdater } from '@/composables/status';
import { usePremium } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import type { TaskMeta } from '@/types/task';

function defaultCompoundStats(): CompoundStats {
  return {
    debtLoss: {},
    interestProfit: {},
    liquidationProfit: {},
    rewards: {},
  };
}

export const useCompoundStore = defineStore('defi/compound', () => {
  const balances = ref<CompoundBalances>({});
  const history = ref<CompoundStats>(defaultCompoundStats());

  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { activeModules } = useModules();
  const premium = usePremium();
  const { t } = useI18n();
  const { fetchCompoundBalances, fetchCompoundStats } = useCompoundApi();

  const { fetchDisabled, resetStatus, setStatus } = useStatusUpdater(Section.DEFI_COMPOUND_BALANCES);

  const rewards = computed(() => toProfitLossModel(get(history).rewards));
  const interestProfit = computed(() => toProfitLossModel(get(history).interestProfit));
  const debtLoss = computed(() => toProfitLossModel(get(history).debtLoss));
  const liquidationProfit = computed(() => toProfitLossModel(get(history).liquidationProfit));

  const fetchBalances = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.COMPOUND))
      return;

    if (fetchDisabled(refresh))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);

    try {
      const taskType = TaskType.DEFI_COMPOUND_BALANCES;
      const { taskId } = await fetchCompoundBalances();
      const { result } = await awaitTask<CompoundBalances, TaskMeta>(taskId, taskType, {
        title: t('actions.defi.compound.task.title'),
      });
      set(balances, CompoundBalances.parse(result));
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.defi.compound.error.description', {
            error: error.message,
          }),
          title: t('actions.defi.compound.error.title'),
        });
      }
    }
    setStatus(Status.LOADED);
  };

  const fetchStats = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.COMPOUND) || !get(premium))
      return;

    const section = { section: Section.DEFI_COMPOUND_STATS };

    if (fetchDisabled(refresh, section))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const taskType = TaskType.DEFI_COMPOUND_STATS;
      const { taskId } = await fetchCompoundStats();
      const { result } = await awaitTask<CompoundStats, TaskMeta>(taskId, taskType, {
        title: t('actions.defi.compound_history.task.title'),
      });

      set(history, CompoundStats.parse(result));
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          display: true,
          message: t('actions.defi.compound_history.error.description', {
            error: error.message,
          }),
          title: t('actions.defi.compound_history.error.title'),
        });
      }
    }
    setStatus(Status.LOADED, section);
  };

  const reset = (): void => {
    set(balances, {});
    set(history, defaultCompoundStats());
    resetStatus();
    resetStatus({ section: Section.DEFI_COMPOUND_STATS });
  };

  const addresses = computed<string[]>(() => getProtocolAddresses(get(balances), get(history)));

  return {
    addresses,
    balances,
    debtLoss,
    fetchBalances,
    fetchStats,
    history,
    interestProfit,
    liquidationProfit,
    reset,
    rewards,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useCompoundStore, import.meta.hot));
