import type { TaskMeta } from '@/modules/core/tasks/types';
import {
  LiquityBalancesWithCollateralInfo,
  LiquityPoolDetails,
  LiquityStakingDetails,
  LiquityStatistics,
} from '@rotki/common';
import { logger } from '@/modules/core/common/logging/logging';
import { Module } from '@/modules/core/common/modules';
import { Section, Status } from '@/modules/core/common/status';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { usePremium } from '@/modules/premium/use-premium';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useStatusUpdater } from '@/modules/shell/sync-progress/use-status-updater';
import { useLiquityApi } from '@/modules/staking/liquity/use-liquity-api';
import { useLiquityStore } from '@/modules/staking/liquity/use-liquity-store';

interface UseLiquityDataFetchingReturn {
  fetchBalances: (refresh?: boolean) => Promise<void>;
  fetchPools: (refresh?: boolean) => Promise<void>;
  fetchStaking: (refresh?: boolean) => Promise<void>;
  fetchStatistics: (refresh?: boolean) => Promise<void>;
}

export function useLiquityDataFetching(): UseLiquityDataFetchingReturn {
  const isPremium = usePremium();
  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const { t } = useI18n({ useScope: 'global' });
  const { runTask } = useTaskHandler();
  const { isTaskRunning } = useTaskStore();
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

  function canFetch(taskType: TaskType, section: Section, refresh: boolean): { proceed: boolean; setStatus: (status: Status) => void } {
    const { getStatus, setStatus } = useStatusUpdater(section);

    if (!isModuleActive() || isTaskRunning(taskType) || (getStatus() === Status.LOADED && !refresh))
      return { proceed: false, setStatus };

    return { proceed: true, setStatus };
  }

  function handleFailure(taskType: TaskType, outcome: { message: string; error?: unknown }, errorTitle: string, errorMessage: string): void {
    logger.error(`action failure for task ${TaskType[taskType]}:`, outcome.error);
    const { notifyError } = useNotifications();
    notifyError(errorTitle, errorMessage);
  }

  async function fetchBalances(refresh = false): Promise<void> {
    const { proceed, setStatus } = canFetch(TaskType.LIQUITY_BALANCES, Section.DEFI_LIQUITY_BALANCES, refresh);
    if (!proceed)
      return;

    setStatus(refresh ? Status.REFRESHING : Status.LOADING);

    const outcome = await runTask<LiquityBalancesWithCollateralInfo, TaskMeta>(
      async () => fetchLiquityBalances(),
      { type: TaskType.LIQUITY_BALANCES, meta: { title: t('actions.defi.liquity.task.title') }, guard: false },
    );

    if (outcome.success) {
      set(balances, LiquityBalancesWithCollateralInfo.parse(outcome.result));
    }
    else if (isActionableFailure(outcome)) {
      handleFailure(
        TaskType.LIQUITY_BALANCES,
        outcome,
        t('actions.defi.liquity_balances.error.title'),
        t('actions.defi.liquity_balances.error.description', { message: outcome.message }),
      );
    }

    setStatus(Status.LOADED);
  }

  async function fetchPools(refresh = false): Promise<void> {
    if (!get(isPremium))
      return;

    const { proceed, setStatus } = canFetch(TaskType.LIQUITY_STAKING_POOLS, Section.DEFI_LIQUITY_STAKING_POOLS, refresh);
    if (!proceed)
      return;

    setStatus(refresh ? Status.REFRESHING : Status.LOADING);

    const outcome = await runTask<LiquityPoolDetails, TaskMeta>(
      async () => fetchLiquityStakingPools(),
      { type: TaskType.LIQUITY_STAKING_POOLS, meta: { title: t('actions.defi.liquity_pools.task.title') }, guard: false },
    );

    if (outcome.success) {
      set(stakingPools, LiquityPoolDetails.parse(outcome.result));
    }
    else if (isActionableFailure(outcome)) {
      handleFailure(
        TaskType.LIQUITY_STAKING_POOLS,
        outcome,
        t('actions.defi.liquity_pools.error.title'),
        t('actions.defi.liquity_pools.error.description', { message: outcome.message }),
      );
    }

    setStatus(Status.LOADED);
  }

  async function fetchStaking(refresh = false): Promise<void> {
    if (!get(isPremium))
      return;

    const { proceed, setStatus } = canFetch(TaskType.LIQUITY_STAKING, Section.DEFI_LIQUITY_STAKING, refresh);
    if (!proceed)
      return;

    setStatus(refresh ? Status.REFRESHING : Status.LOADING);

    const outcome = await runTask<LiquityStakingDetails, TaskMeta>(
      async () => fetchLiquityStaking(),
      { type: TaskType.LIQUITY_STAKING, meta: { title: t('actions.defi.liquity_staking.task.title') }, guard: false },
    );

    if (outcome.success) {
      set(staking, LiquityStakingDetails.parse(outcome.result));
    }
    else if (isActionableFailure(outcome)) {
      handleFailure(
        TaskType.LIQUITY_STAKING,
        outcome,
        t('actions.defi.liquity_staking.error.title'),
        t('actions.defi.liquity_staking.error.description', { message: outcome.message }),
      );
    }

    setStatus(Status.LOADED);
  }

  async function fetchStatistics(refresh = false): Promise<void> {
    if (!get(isPremium))
      return;

    const { proceed, setStatus } = canFetch(TaskType.LIQUITY_STATISTICS, Section.DEFI_LIQUITY_STATISTICS, refresh);
    if (!proceed)
      return;

    setStatus(refresh ? Status.REFRESHING : Status.LOADING);

    const outcome = await runTask<LiquityStatistics, TaskMeta>(
      async () => fetchLiquityStatistics(),
      { type: TaskType.LIQUITY_STATISTICS, meta: { title: t('actions.defi.liquity_statistics.task.title') }, guard: false },
    );

    if (outcome.success) {
      set(statistics, LiquityStatistics.parse(outcome.result));
    }
    else if (isActionableFailure(outcome)) {
      handleFailure(
        TaskType.LIQUITY_STATISTICS,
        outcome,
        t('actions.defi.liquity_statistics.error.title'),
        t('actions.defi.liquity_statistics.error.description', { message: outcome.message }),
      );
    }

    setStatus(Status.LOADED);
  }

  return {
    fetchBalances,
    fetchPools,
    fetchStaking,
    fetchStatistics,
  };
}
