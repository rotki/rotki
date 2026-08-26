import type { ComputedRef, MaybeRef, Ref } from 'vue';
import { assert, Blockchain, type EthStakingPayload, type EthStakingPerformance, type EthStakingPerformanceResponse } from '@rotki/common';
import { omit } from 'es-toolkit';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { isAccountWithBalanceValidator } from '@/modules/accounts/account-helpers';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { usePremium } from '@/modules/premium/use-premium';
import { useEth2Api } from '@/modules/staking/api/use-eth2-api';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseEth2StakingReturn {
  performance: ComputedRef<EthStakingPerformance>;
  pagination: Ref<EthStakingPayload>;
  performanceLoading: Ref<boolean>;
  fetchPerformance: (payload: EthStakingPayload) => Promise<void>;
  refreshPerformance: (userInitiated: boolean) => Promise<void>;
}

export function useEth2Staking(): UseEth2StakingReturn {
  const defaultPagination = (): EthStakingPayload => ({
    limit: 10,
    offset: 0,
  });

  const modelPagination = ref<EthStakingPayload>(defaultPagination());

  const premium = usePremium();
  const { statusOf, submitTask } = useNativeTask();
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });

  const api = useEth2Api();

  const { getBlockchainAccounts } = useBlockchainAccountData();

  async function syncEthStakingPerformance(userInitiated = false): Promise<boolean> {
    if (!get(premium))
      return false;

    // `fetchDisabled(refresh)` on the orchestrator projection: skip cached loads and re-entrancy.
    const status = statusOf(ActivityKind.STAKING, ActivityPart.PERFORMANCE);
    if ((status.everCompleted && !userInitiated) || status.active)
      return false;

    const defaults: EthStakingPayload = {
      limit: 0,
      offset: 0,
    };

    // The performance data itself is read separately via `fetchPerformance`; this activity only
    // refreshes the backend cache, so the success mapper has no store side effect.
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.STAKING, ActivityPart.PERFORMANCE),
      kind: ActivityKind.STAKING,
      rerunnable: true,
      staleAfter: [{ kind: ActivityKind.STAKING, parts: [ActivityPart.ADD] }],
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<EthStakingPerformanceResponse>(
          async () => api.refreshStakingPerformance(defaults),
        ),
        () => {},
      ),
      subtitle: activityLabel(ActivityKind.STAKING, ActivityPart.PERFORMANCE),
      title: t('task_center.group.staking'),
    });

    onActionableError(outcome, (error) => {
      logger.error(error.message);
      notifyError(
        t('actions.staking.eth2.error.title'),
        t('actions.staking.eth2.error.description', {
          error: error.message,
        }),
      );
    });

    return !isErr(outcome);
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
    await fetchPerformance(get(modelPagination));

    const success = await syncEthStakingPerformance(userInitiated);
    if (success) {
      // We unref here to make sure that we use the latest modelPagination
      await fetchPerformance(get(modelPagination));
    }
  }

  watch(modelPagination, async modelPagination => fetchPerformance(modelPagination));

  return {
    fetchPerformance,
    pagination: modelPagination,
    performance,
    performanceLoading,
    refreshPerformance,
  };
}
