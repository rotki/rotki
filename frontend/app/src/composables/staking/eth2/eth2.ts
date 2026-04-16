import type { ComputedRef, MaybeRef, Ref } from 'vue';
import type { TaskMeta } from '@/modules/tasks/types';
import { assert, Blockchain, type EthStakingPayload, type EthStakingPerformance, type EthStakingPerformanceResponse } from '@rotki/common';
import { omit } from 'es-toolkit';
import { useEth2Api } from '@/composables/api/staking/eth2';
import { usePremium } from '@/composables/premium';
import { useStatusUpdater } from '@/composables/status';
import { isAccountWithBalanceValidator } from '@/modules/accounts/account-helpers';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { logger } from '@/modules/common/logging/logging';
import { Section, Status } from '@/modules/common/status';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';

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
  const { runTask } = useTaskHandler();
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });

  const api = useEth2Api();

  const { getBlockchainAccounts } = useBlockchainAccountData();

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

    setStatus(userInitiated ? Status.REFRESHING : Status.LOADING);
    const outcome = await runTask<EthStakingPerformanceResponse, TaskMeta>(
      async () => api.refreshStakingPerformance(defaults),
      { type: taskType, meta: { title: t('actions.staking.eth2.task.title') } },
    );

    if (outcome.success) {
      setStatus(Status.LOADED);
      return true;
    }

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      notifyError(
        t('actions.staking.eth2.error.title'),
        t('actions.staking.eth2.error.description', {
          error: outcome.message,
        }),
      );
    }
    resetStatus();
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
        const consolidatedInto = validator?.data?.consolidatedInto;
        const total = validator?.amount;
        return {
          consolidatedInto,
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
