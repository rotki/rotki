import {
  Blockchain,
  type EthStakingPayload,
  type EthStakingPerformance,
  type EthStakingPerformanceResponse,
} from '@rotki/common';
import { omit } from 'es-toolkit';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';
import { isAccountWithBalanceValidator } from '@/utils/blockchain/accounts';
import { isTaskCancelled } from '@/utils';
import { useNotificationsStore } from '@/store/notifications';
import { useBlockchainStore } from '@/store/blockchain';
import { useTaskStore } from '@/store/tasks';
import { useEth2Api } from '@/composables/api/staking/eth2';
import { useStatusUpdater } from '@/composables/status';
import { usePremium } from '@/composables/premium';
import type { MaybeRef } from '@vueuse/core';
import type { TaskMeta } from '@/types/task';
import type { ComputedRef, Ref } from 'vue';

interface UseEthStakingReturn {
  performance: ComputedRef<EthStakingPerformance>;
  pagination: Ref<EthStakingPayload>;
  performanceLoading: Ref<boolean>;
  fetchPerformance: (payload: EthStakingPayload) => Promise<void>;
  refreshPerformance: (userInitiated: boolean) => Promise<void>;
}

export function useEth2Staking(): UseEthStakingReturn {
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

  const { getBlockchainAccounts } = useBlockchainStore();

  async function syncEthStakingPerformance(userInitiated = false): Promise<boolean> {
    if (!get(premium))
      return false;

    const taskType = TaskType.STAKING_ETH2;

    const { fetchDisabled, resetStatus, setStatus } = useStatusUpdater(Section.STAKING_ETH2);

    if (fetchDisabled(userInitiated))
      return false;

    const defaults: EthStakingPayload = {
      limit: 0,
      offset: 0,
    };

    try {
      setStatus(userInitiated ? Status.REFRESHING : Status.LOADING);
      const { taskId } = await api.refreshStakingPerformance(defaults);
      await awaitTask<EthStakingPerformanceResponse, TaskMeta>(taskId, taskType, {
        title: t('actions.staking.eth2.task.title'),
      });

      setStatus(Status.LOADED);
      return true;
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          display: true,
          message: t('actions.staking.eth2.error.description', {
            error: error.message,
          }),
          title: t('actions.staking.eth2.error.title'),
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
    return api.fetchStakingPerformance(get(payload));
  };

  const {
    execute,
    isLoading: performanceLoading,
    state,
  } = useAsyncState<EthStakingPerformanceResponse, MaybeRef<EthStakingPayload>[]>(
    fetchStakingPerformance,
    {
      entriesFound: 0,
      entriesTotal: 0,
      sums: {},
      validators: {},
    } satisfies EthStakingPerformanceResponse,
    {
      delay: 0,
      immediate: false,
      onError: (error) => {
        logger.error(error);
      },
      resetOnExecute: false,
    },
  );

  const performance = computed<EthStakingPerformance>(() => {
    const performance = get(state);
    const accounts = getBlockchainAccounts(Blockchain.ETH2).filter(isAccountWithBalanceValidator);
    return {
      ...omit(performance, ['validators']),
      validators: Object.entries(performance.validators).map(([idx, value]) => {
        const index = parseInt(idx);

        const validator = accounts.find(x => x.data.index === index);
        const status = validator?.data?.status;
        const total = validator?.amount;
        return {
          index,
          status,
          total,
          ...value,
        };
      }),
    };
  });

  const fetchPerformance = async (payload: EthStakingPayload): Promise<void> => {
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

  watch(pagination, async pagination => fetchPerformance(pagination));

  return {
    fetchPerformance,
    pagination,
    performance,
    performanceLoading,
    refreshPerformance,
  };
}
