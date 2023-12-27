import { type ProfitLossModel } from '@rotki/common/lib/defi';
import { AaveBalances, AaveHistory } from '@rotki/common/lib/defi/aave';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { type TaskMeta, UserCancelledTaskError } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const useAaveStore = defineStore('defi/aave', () => {
  const balances: Ref<AaveBalances> = ref({});
  const history: Ref<AaveHistory> = ref({});

  const { notify } = useNotificationsStore();
  const { awaitTask } = useTaskStore();
  const { activeModules } = useModules();
  const premium = usePremium();
  const { t } = useI18n();

  const { fetchAaveBalances, fetchAaveHistory } = useAaveApi();

  const { resetStatus, setStatus, fetchDisabled } = useStatusUpdater(
    Section.DEFI_AAVE_BALANCES
  );

  const aaveTotalEarned = (addresses: string[]) =>
    computed(() => {
      const earned: ProfitLossModel[] = [];
      const aaveHistory = get(history);

      for (const address in aaveHistory) {
        if (addresses.length > 0 && !addresses.includes(address)) {
          continue;
        }
        const totalEarned = aaveHistory[address].totalEarnedInterest;
        for (const asset in totalEarned) {
          const index = earned.findIndex(e => e.asset === asset);
          if (index < 0) {
            earned.push({
              address: '',
              asset,
              value: totalEarned[asset]
            });
          } else {
            earned[index] = {
              ...earned[index],
              value: balanceSum(earned[index].value, totalEarned[asset])
            };
          }
        }
      }
      return earned;
    });

  const fetchBalances = async (refresh = false) => {
    if (!get(activeModules).includes(Module.AAVE)) {
      return;
    }
    if (fetchDisabled(refresh)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);

    try {
      const taskType = TaskType.AAVE_BALANCES;
      const { taskId } = await fetchAaveBalances();
      const { result } = await awaitTask<AaveBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.defi.aave_balances.task.title')
        }
      );
      set(balances, AaveBalances.parse(result));
    } catch (e: any) {
      if (e instanceof UserCancelledTaskError) {
        logger.debug(e);
      } else {
        const message = t('actions.defi.aave_balances.error.description', {
          error: e.message
        });
        const title = t('actions.defi.aave_balances.error.title');
        notify({
          title,
          message,
          display: true
        });
      }
    }

    setStatus(Status.LOADED);
  };

  const fetchHistory = async (payload: { refresh?: boolean }) => {
    if (!get(activeModules).includes(Module.AAVE) || !get(premium)) {
      return;
    }

    const section = Section.DEFI_AAVE_HISTORY;
    const refresh = payload?.refresh;

    if (fetchDisabled(!!refresh, section)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const taskType = TaskType.AAVE_HISTORY;
      const { taskId } = await fetchAaveHistory();
      const { result } = await awaitTask<AaveHistory, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.defi.aave_history.task.title')
        }
      );

      set(history, AaveHistory.parse(result));
    } catch (e: any) {
      if (e instanceof UserCancelledTaskError) {
        logger.debug(e);
      } else {
        logger.error(e);
        const message = t('actions.defi.aave_history.error.description', {
          error: e.message
        });
        const title = t('actions.defi.aave_history.error.title');

        notify({
          title,
          message,
          display: true
        });
      }
    }

    setStatus(Status.LOADED, section);
  };

  const reset = () => {
    set(balances, {});
    set(history, {});
    resetStatus();
    resetStatus(Section.DEFI_AAVE_HISTORY);
  };

  const addresses: ComputedRef<string[]> = computed(() =>
    getProtocolAddresses(get(balances), get(history))
  );

  return {
    balances,
    history,
    addresses,
    aaveTotalEarned,
    fetchBalances,
    fetchHistory,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAaveStore, import.meta.hot));
}
