import { CompoundBalances, CompoundStats } from '@/types/defi/compound';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { taskCancelledError } from '@/utils';

const defaultCompoundStats = (): CompoundStats => ({
  debtLoss: {},
  interestProfit: {},
  rewards: {},
  liquidationProfit: {}
});

export const useCompoundStore = defineStore('defi/compound', () => {
  const balances: Ref<CompoundBalances> = ref({});
  const history: Ref<CompoundStats> = ref(defaultCompoundStats());

  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { activeModules } = useModules();
  const premium = usePremium();
  const { t } = useI18n();
  const { fetchCompoundBalances, fetchCompoundStats } = useCompoundApi();

  const { resetStatus, setStatus, fetchDisabled } = useStatusUpdater(
    Section.DEFI_COMPOUND_BALANCES
  );

  const rewards = computed(() => toProfitLossModel(get(history).rewards));
  const interestProfit = computed(() =>
    toProfitLossModel(get(history).interestProfit)
  );
  const debtLoss = computed(() => toProfitLossModel(get(history).debtLoss));
  const liquidationProfit = computed(() =>
    toProfitLossModel(get(history).liquidationProfit)
  );

  const fetchBalances = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.COMPOUND)) {
      return;
    }

    if (fetchDisabled(refresh)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);

    try {
      const taskType = TaskType.DEFI_COMPOUND_BALANCES;
      const { taskId } = await fetchCompoundBalances();
      const { result } = await awaitTask<CompoundBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.defi.compound.task.title')
        }
      );
      set(balances, CompoundBalances.parse(result));
    } catch (e: any) {
      if (!taskCancelledError(e)) {
        notify({
          title: t('actions.defi.compound.error.title'),
          message: t('actions.defi.compound.error.description', {
            error: e.message
          }),
          display: true
        });
      }
    }
    setStatus(Status.LOADED);
  };

  const fetchStats = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.COMPOUND) || !get(premium)) {
      return;
    }

    const section = Section.DEFI_COMPOUND_STATS;

    if (fetchDisabled(refresh, section)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const taskType = TaskType.DEFI_COMPOUND_STATS;
      const { taskId } = await fetchCompoundStats();
      const { result } = await awaitTask<CompoundStats, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.defi.compound_history.task.title')
        }
      );

      set(history, CompoundStats.parse(result));
    } catch (e: any) {
      if (!taskCancelledError(e)) {
        logger.error(e);
        notify({
          title: t('actions.defi.compound_history.error.title'),
          message: t('actions.defi.compound_history.error.description', {
            error: e.message
          }),
          display: true
        });
      }
    }
    setStatus(Status.LOADED, section);
  };

  const reset = (): void => {
    set(balances, {});
    set(history, defaultCompoundStats());
    resetStatus();
    resetStatus(Section.DEFI_COMPOUND_STATS);
  };

  const addresses: ComputedRef<string[]> = computed(() =>
    getProtocolAddresses(get(balances), get(history))
  );

  return {
    balances,
    history,
    rewards,
    interestProfit,
    debtLoss,
    liquidationProfit,
    addresses,
    fetchBalances,
    fetchStats,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useCompoundStore, import.meta.hot));
}
