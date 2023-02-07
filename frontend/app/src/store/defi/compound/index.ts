import { type Ref } from 'vue';
import { CompoundBalances, CompoundHistory } from '@/types/defi/compound';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';
import { toProfitLossModel } from '@/utils/defi';
import { isLoading } from '@/utils/status';

const defaultCompoundHistory = (): CompoundHistory => ({
  events: [],
  debtLoss: {},
  interestProfit: {},
  rewards: {},
  liquidationProfit: {}
});

export const useCompoundStore = defineStore('defi/compound', () => {
  const balances: Ref<CompoundBalances> = ref({});
  const history: Ref<CompoundHistory> = ref(defaultCompoundHistory());

  const { resetStatus } = useStatusUpdater(Section.DEFI_COMPOUND_BALANCES);
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { activeModules } = useModules();
  const premium = usePremium();
  const { tc } = useI18n();
  const { fetchCompoundBalances, fetchCompoundHistory } = useCompoundApi();

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

    const section = Section.DEFI_COMPOUND_BALANCES;
    const currentStatus = getStatus(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const taskType = TaskType.DEFI_COMPOUND_BALANCES;
      const { taskId } = await fetchCompoundBalances();
      const { result } = await awaitTask<CompoundBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: tc('actions.defi.compound.task.title')
        }
      );
      set(balances, CompoundBalances.parse(result));
    } catch (e: any) {
      notify({
        title: tc('actions.defi.compound.error.title'),
        message: tc('actions.defi.compound.error.description', undefined, {
          error: e.message
        }),
        display: true
      });
    }
    setStatus(Status.LOADED, section);
  };

  const fetchHistory = async (refresh = false): Promise<void> => {
    if (!get(activeModules).includes(Module.COMPOUND) || !get(premium)) {
      return;
    }

    const section = Section.DEFI_COMPOUND_HISTORY;
    const currentStatus = getStatus(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const taskType = TaskType.DEFI_COMPOUND_HISTORY;
      const { taskId } = await fetchCompoundHistory();
      const { result } = await awaitTask<CompoundHistory, TaskMeta>(
        taskId,
        taskType,
        {
          title: tc('actions.defi.compound_history.task.title')
        }
      );

      set(history, CompoundHistory.parse(result));
    } catch (e: any) {
      logger.error(e);
      notify({
        title: tc('actions.defi.compound_history.error.title'),
        message: tc(
          'actions.defi.compound_history.error.description',
          undefined,
          {
            error: e.message
          }
        ),
        display: true
      });
    }
    setStatus(Status.LOADED, section);
  };

  const reset = (): void => {
    set(balances, {});
    set(history, defaultCompoundHistory());
    resetStatus(Section.DEFI_COMPOUND_BALANCES);
    resetStatus(Section.DEFI_COMPOUND_HISTORY);
  };

  return {
    balances,
    history,
    rewards,
    interestProfit,
    debtLoss,
    liquidationProfit,
    fetchBalances,
    fetchHistory,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useCompoundStore, import.meta.hot));
}
