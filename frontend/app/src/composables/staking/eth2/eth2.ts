import { type MaybeRef, objectOmit } from '@vueuse/core';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import type {
  EthStakingPayload,
  EthStakingPerformance,
  EthStakingPerformanceResponse,
} from '@rotki/common/lib/staking/eth2';
import type { TaskMeta } from '@/types/task';

export function useEth2Staking() {
  const defaultPagination = (): EthStakingPayload => ({
    limit: 10,
    offset: 0,
  });

  const pagination = ref<EthStakingPayload>(defaultPagination());

  const premium = usePremium();
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const api = useEth2Api();

  const { eth2Validators } = storeToRefs(useEthAccountsStore());
  const { stakingBalances } = storeToRefs(useEthBalancesStore());

  async function syncEthStakingPerformance(userInitiated = false): Promise<boolean> {
    if (!get(premium))
      return false;

    const taskType = TaskType.STAKING_ETH2;

    const { setStatus, resetStatus, fetchDisabled } = useStatusUpdater(Section.STAKING_ETH2);

    if (fetchDisabled(userInitiated))
      return false;

    const defaults: EthStakingPayload = {
      limit: 0,
      offset: 0,
    };

    try {
      setStatus(userInitiated ? Status.REFRESHING : Status.LOADING);
      const { taskId } = await api.refreshStakingPerformance(defaults);
      await awaitTask<EthStakingPerformanceResponse, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.staking.eth2.task.title'),
        },
      );

      setStatus(Status.LOADED);
      return true;
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          title: t('actions.staking.eth2.error.title'),
          message: t('actions.staking.eth2.error.description', {
            error: error.message,
          }),
          display: true,
        });
      }
      resetStatus();
    }
    return false;
  }

  const fetchStakingPerformance = async (
    payload: MaybeRef<EthStakingPayload>,
  ): Promise<EthStakingPerformanceResponse> => {
    assert(get(premium));
    return await api.fetchStakingPerformance(get(payload));
  };

  const {
    state,
    execute,
    isLoading: performanceLoading,
  } = useAsyncState<EthStakingPerformanceResponse, MaybeRef<EthStakingPayload>[]>(
    fetchStakingPerformance,
      {
        validators: {},
        entriesFound: 0,
        entriesTotal: 0,
        sums: {},
      } satisfies EthStakingPerformanceResponse,
      {
        immediate: false,
        resetOnExecute: false,
        delay: 0,
        onError: (error) => {
          logger.error(error);
        },
      },
  );

  const performance = computed<EthStakingPerformance>(() => {
    const performance = get(state);
    const validators = get(eth2Validators);
    const balances = get(stakingBalances);
    return {
      ...objectOmit(performance, ['validators']),
      validators: Object.entries(performance.validators).map(([idx, value]) => {
        const index = parseInt(idx);

        const validator = validators.entries.find(x => x.index === index);
        const status = validator?.status;
        const total = validator ? balances.find(x => x.publicKey === validator.publicKey)?.amount : undefined;
        return ({
          index,
          status,
          total,
          ...value,
        });
      }),
    };
  });

  const fetchPerformance = async (
    payload: EthStakingPayload,
  ): Promise<void> => {
    await execute(0, payload);
  };

  async function refreshPerformance(userInitiated: boolean): Promise<void> {
    await fetchPerformance(get(pagination));

    const success = await syncEthStakingPerformance(userInitiated);
    if (success) {
      // We unref here to make sure that we use the latest pagination
      await fetchPerformance(get(pagination));
    }
  }

  watch(pagination, pagination => fetchPerformance(pagination));

  return {
    performance,
    pagination,
    performanceLoading,
    fetchPerformance,
    refreshPerformance,
  };
}
