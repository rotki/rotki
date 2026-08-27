import type { PendingTask } from '@/modules/core/tasks/types';
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

/** What separates one liquity fetch from another; everything else is shared. */
interface FetchDefinition {
  /** The user-facing failure description, given the backend's message. */
  errorDescription: (message: string) => string;
  /** The user-facing failure title. */
  errorTitle: () => string;
  /** Which part of the liquity activity this fetch reports as. */
  part: ActivityPart;
  /** Whether the fetch needs premium. Balances are free; the backend rejects the other three. */
  premiumOnly: boolean;
  /** Starts the backend query, which runs as a task. */
  query: () => Promise<PendingTask>;
  /** Validates the response and writes it to the store. */
  store: (result: unknown) => void;
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
   * Whether a fetch should go ahead.
   *
   * @remarks
   * Skipped when the module is off, an activity for this part is already live, or it has completed
   * before and this is not a refresh. The components read that same activity for their loading
   * display, so there is no second copy of this state to keep in step.
   */
  function canFetch(part: ActivityPart, refresh: boolean): boolean {
    const status = statusOf(ActivityKind.LIQUITY, part);
    return isModuleActive() && !status.active && (!status.everCompleted || refresh);
  }

  /**
   * Wraps one {@link FetchDefinition} in the task shape, the guards and the failure handling that
   * all four liquity fetches share.
   */
  function createFetch(definition: FetchDefinition): (refresh?: boolean) => Promise<void> {
    const { errorDescription, errorTitle, part, premiumOnly, query, store } = definition;

    return async (refresh = false): Promise<void> => {
      if (premiumOnly && !get(isPremium))
        return;

      if (!canFetch(part, refresh))
        return;

      const outcome = await submitTask({
        id: makeActivityId(ActivityKind.LIQUITY, part),
        kind: ActivityKind.LIQUITY,
        rerunnable: true,
        // Derived from decoded history events, so a completed decode makes this stale.
        staleAfter: [{ kind: ActivityKind.TX_DECODING }],
        run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
          await runTask<unknown>(async () => query()),
          store,
        ),
        subtitle: activityLabel(ActivityKind.LIQUITY, part),
        title: t('task_center.group.liquity'),
      });

      onActionableError(outcome, (error) => {
        logger.error(`action failure for liquity ${part}:`, error);
        notifyError(errorTitle(), errorDescription(error.message));
      });
    };
  }

  const fetchBalances = createFetch({
    errorDescription: (message: string) => t('actions.defi.liquity_balances.error.description', { message }),
    errorTitle: () => t('actions.defi.liquity_balances.error.title'),
    part: ActivityPart.BALANCES,
    premiumOnly: false,
    query: async () => fetchLiquityBalances(),
    store: (result) => {
      set(balances, LiquityBalancesWithCollateralInfo.parse(result));
    },
  });

  const fetchPools = createFetch({
    errorDescription: (message: string) => t('actions.defi.liquity_pools.error.description', { message }),
    errorTitle: () => t('actions.defi.liquity_pools.error.title'),
    part: ActivityPart.POOLS,
    premiumOnly: true,
    query: async () => fetchLiquityStakingPools(),
    store: (result) => {
      set(stakingPools, LiquityPoolDetails.parse(result));
    },
  });

  const fetchStaking = createFetch({
    errorDescription: (message: string) => t('actions.defi.liquity_staking.error.description', { message }),
    errorTitle: () => t('actions.defi.liquity_staking.error.title'),
    part: ActivityPart.STAKE,
    premiumOnly: true,
    query: async () => fetchLiquityStaking(),
    store: (result) => {
      set(staking, LiquityStakingDetails.parse(result));
    },
  });

  const fetchStatistics = createFetch({
    errorDescription: (message: string) => t('actions.defi.liquity_statistics.error.description', { message }),
    errorTitle: () => t('actions.defi.liquity_statistics.error.title'),
    part: ActivityPart.STATISTICS,
    premiumOnly: true,
    query: async () => fetchLiquityStatistics(),
    store: (result) => {
      set(statistics, LiquityStatistics.parse(result));
    },
  });

  return {
    fetchBalances,
    fetchPools,
    fetchStaking,
    fetchStatistics,
  };
}
