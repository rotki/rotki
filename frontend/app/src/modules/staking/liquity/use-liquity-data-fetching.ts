import {
  LiquityBalancesWithCollateralInfo,
  LiquityPoolDetails,
  LiquityStakingDetails,
  LiquityStatistics,
} from '@rotki/common';
import { map as mapResult, type Result } from 'plainfp/result';
import { logger } from '@/modules/core/common/logging/logging';
import { Module } from '@/modules/core/common/modules';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { usePremium } from '@/modules/premium/use-premium';
import { useSetting } from '@/modules/settings/use-setting';
import { useLiquityApi } from '@/modules/staking/liquity/use-liquity-api';
import { useLiquityStore } from '@/modules/staking/liquity/use-liquity-store';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseLiquityDataFetchingReturn {
  fetchBalances: (refresh?: boolean) => Promise<void>;
  fetchPools: (refresh?: boolean) => Promise<void>;
  fetchStaking: (refresh?: boolean) => Promise<void>;
  fetchStatistics: (refresh?: boolean) => Promise<void>;
}

export function useLiquityDataFetching(): UseLiquityDataFetchingReturn {
  const isPremium = usePremium();
  const activeModules = useSetting('activeModules');
  const { t } = useI18n({ useScope: 'global' });
  const { statusOf, submitTask } = useNativeTask();
  const { notifyError } = useNotifications();
  const {
    fetchLiquityBalances,
    fetchLiquityStaking,
    fetchLiquityStakingPools,
    fetchLiquityStatistics,
  } = useLiquityApi();
  const { balances, staking, stakingPools, statistics } = storeToRefs(useLiquityStore());

  function isModuleActive(): boolean {
    return get(activeModules).includes(Module.LIQUITY);
  }

  /**
   * Skip when the module is off, an activity for this part is already live, or it has completed
   * before and this is not a refresh. The components read the same activity for their loading
   * display, so there is no second copy of this state to keep in step.
   */
  function canFetch(part: ActivityPart, refresh: boolean): boolean {
    const status = statusOf(ActivityKind.LIQUITY, part);
    return isModuleActive() && !status.active && (!status.everCompleted || refresh);
  }

  function notifyFailure(part: ActivityPart, error: TaskError, errorTitle: string, errorMessage: string): void {
    logger.error(`action failure for liquity ${part}:`, error);
    notifyError(errorTitle, errorMessage);
  }

  async function fetchBalances(refresh = false): Promise<void> {
    if (!canFetch(ActivityPart.BALANCES, refresh))
      return;

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.LIQUITY, ActivityPart.BALANCES),
      kind: ActivityKind.LIQUITY,
      rerunnable: true,
      // Derived from decoded history events, so a completed decode makes this stale. Restores what
      // `clearDependedSection` did before it was deleted.
      staleAfter: [{ kind: ActivityKind.TX_DECODING }],
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<LiquityBalancesWithCollateralInfo>(
          async () => fetchLiquityBalances(),
        ),
        (result) => {
          set(balances, LiquityBalancesWithCollateralInfo.parse(result));
        },
      ),
      subtitle: activityLabel(ActivityKind.LIQUITY, ActivityPart.BALANCES),
      title: t('task_center.group.liquity'),
    });

    onActionableError(outcome, (error) => {
      notifyFailure(
        ActivityPart.BALANCES,
        error,
        t('actions.defi.liquity_balances.error.title'),
        t('actions.defi.liquity_balances.error.description', { message: error.message }),
      );
    });
  }

  async function fetchPools(refresh = false): Promise<void> {
    if (!get(isPremium))
      return;

    if (!canFetch(ActivityPart.POOLS, refresh))
      return;

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.LIQUITY, ActivityPart.POOLS),
      kind: ActivityKind.LIQUITY,
      rerunnable: true,
      // Derived from decoded history events, so a completed decode makes this stale. Restores what
      // `clearDependedSection` did before it was deleted.
      staleAfter: [{ kind: ActivityKind.TX_DECODING }],
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<LiquityPoolDetails>(
          async () => fetchLiquityStakingPools(),
        ),
        (result) => {
          set(stakingPools, LiquityPoolDetails.parse(result));
        },
      ),
      subtitle: activityLabel(ActivityKind.LIQUITY, ActivityPart.POOLS),
      title: t('task_center.group.liquity'),
    });

    onActionableError(outcome, (error) => {
      notifyFailure(
        ActivityPart.POOLS,
        error,
        t('actions.defi.liquity_pools.error.title'),
        t('actions.defi.liquity_pools.error.description', { message: error.message }),
      );
    });
  }

  async function fetchStaking(refresh = false): Promise<void> {
    if (!get(isPremium))
      return;

    if (!canFetch(ActivityPart.STAKING, refresh))
      return;

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.LIQUITY, ActivityPart.STAKING),
      kind: ActivityKind.LIQUITY,
      rerunnable: true,
      // Derived from decoded history events, so a completed decode makes this stale. Restores what
      // `clearDependedSection` did before it was deleted.
      staleAfter: [{ kind: ActivityKind.TX_DECODING }],
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<LiquityStakingDetails>(
          async () => fetchLiquityStaking(),
        ),
        (result) => {
          set(staking, LiquityStakingDetails.parse(result));
        },
      ),
      subtitle: activityLabel(ActivityKind.LIQUITY, ActivityPart.STAKING),
      title: t('task_center.group.liquity'),
    });

    onActionableError(outcome, (error) => {
      notifyFailure(
        ActivityPart.STAKING,
        error,
        t('actions.defi.liquity_staking.error.title'),
        t('actions.defi.liquity_staking.error.description', { message: error.message }),
      );
    });
  }

  async function fetchStatistics(refresh = false): Promise<void> {
    if (!get(isPremium))
      return;

    if (!canFetch(ActivityPart.STATISTICS, refresh))
      return;

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.LIQUITY, ActivityPart.STATISTICS),
      kind: ActivityKind.LIQUITY,
      rerunnable: true,
      // Derived from decoded history events, so a completed decode makes this stale. Restores what
      // `clearDependedSection` did before it was deleted.
      staleAfter: [{ kind: ActivityKind.TX_DECODING }],
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<LiquityStatistics>(
          async () => fetchLiquityStatistics(),
        ),
        (result) => {
          set(statistics, LiquityStatistics.parse(result));
        },
      ),
      subtitle: activityLabel(ActivityKind.LIQUITY, ActivityPart.STATISTICS),
      title: t('task_center.group.liquity'),
    });

    onActionableError(outcome, (error) => {
      notifyFailure(
        ActivityPart.STATISTICS,
        error,
        t('actions.defi.liquity_statistics.error.title'),
        t('actions.defi.liquity_statistics.error.description', { message: error.message }),
      );
    });
  }

  return {
    fetchBalances,
    fetchPools,
    fetchStaking,
    fetchStatistics,
  };
}
