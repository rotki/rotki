import type { OnError } from '@/types/fetch';
import type { TaskMeta } from '@/types/task';
import { useLiquityApi } from '@/composables/api/defi/liquity';
import { usePremium } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import { useStatusUpdater } from '@/composables/status';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { fetchDataAsync } from '@/utils/fetch-async';
import {
  type CommonQueryStatusData,
  LiquityBalancesWithCollateralInfo,
  LiquityPoolDetails,
  LiquityStakingDetails,
  LiquityStatistics,
} from '@rotki/common';

const defaultBalances = (): LiquityBalancesWithCollateralInfo => ({ balances: {}, totalCollateralRatio: null });

export const useLiquityStore = defineStore('defi/liquity', () => {
  const balances = ref<LiquityBalancesWithCollateralInfo>(defaultBalances());
  const staking = ref<LiquityStakingDetails>({});
  const stakingPools = ref<LiquityPoolDetails>({});
  const statistics = ref<LiquityStatistics | null>(null);

  const stakingQueryStatus = ref<CommonQueryStatusData>();

  const isPremium = usePremium();
  const { activeModules } = useModules();
  const { t } = useI18n();
  const {
    fetchLiquityBalances,
    fetchLiquityStaking,
    fetchLiquityStakingPools,
    fetchLiquityStatistics,
  } = useLiquityApi();

  const fetchPools = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.liquity_pools.task.title'),
    };

    const onError: OnError = {
      error: message =>
        t('actions.defi.liquity_pools.error.description', {
          message,
        }),
      title: t('actions.defi.liquity_pools.error.title'),
    };

    await fetchDataAsync({
      refresh,
      requires: {
        module: Module.LIQUITY,
        premium: true,
      },
      state: {
        activeModules,
        isPremium,
      },
      task: {
        meta,
        onError,
        parser: result => LiquityPoolDetails.parse(result),
        query: async () => fetchLiquityStakingPools(),
        section: Section.DEFI_LIQUITY_STAKING_POOLS,
        type: TaskType.LIQUITY_STAKING_POOLS,
      },
    }, stakingPools);
  };

  const fetchBalances = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.liquity.task.title'),
    };

    const onError: OnError = {
      error: message => t('actions.defi.liquity_balances.error.description', {
        message,
      }),
      title: t('actions.defi.liquity_balances.error.title'),
    };

    await fetchDataAsync({
      refresh,
      requires: {
        module: Module.LIQUITY,
        premium: false,
      },
      state: {
        activeModules,
        isPremium,
      },
      task: {
        meta,
        onError,
        parser: result => LiquityBalancesWithCollateralInfo.parse(result),
        query: async () => fetchLiquityBalances(),
        section: Section.DEFI_LIQUITY_BALANCES,
        type: TaskType.LIQUITY_BALANCES,
      },
    }, balances);
  };

  const fetchStaking = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.liquity_staking.task.title'),
    };

    const onError: OnError = {
      error: message => t('actions.defi.liquity_staking.error.description', {
        message,
      }),
      title: t('actions.defi.liquity_staking.error.title'),
    };

    await fetchDataAsync({
      refresh,
      requires: {
        module: Module.LIQUITY,
        premium: true,
      },
      state: {
        activeModules,
        isPremium,
      },
      task: {
        meta,
        onError,
        parser: result => LiquityStakingDetails.parse(result),
        query: async () => fetchLiquityStaking(),
        section: Section.DEFI_LIQUITY_STAKING,
        type: TaskType.LIQUITY_STAKING,
      },
    }, staking);
  };

  const fetchStatistics = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.liquity_statistics.task.title'),
    };

    const onError: OnError = {
      error: message =>
        t('actions.defi.liquity_statistics.error.description', {
          message,
        }),
      title: t('actions.defi.liquity_statistics.error.title'),
    };

    await fetchDataAsync({
      refresh,
      requires: {
        module: Module.LIQUITY,
        premium: true,
      },
      state: {
        activeModules,
        isPremium,
      },
      task: {
        meta,
        onError,
        parser: result => LiquityStatistics.parse(result),
        query: async () => fetchLiquityStatistics(),
        section: Section.DEFI_LIQUITY_STATISTICS,
        type: TaskType.LIQUITY_STATISTICS,
      },
    }, statistics);
  };

  const reset = (): void => {
    const { resetStatus } = useStatusUpdater(Section.DEFI_LIQUITY_BALANCES);

    set(balances, defaultBalances());
    set(staking, {});
    set(statistics, null);

    resetStatus({ section: Section.DEFI_LIQUITY_BALANCES });
    resetStatus({ section: Section.DEFI_LIQUITY_STAKING });
    resetStatus({ section: Section.DEFI_LIQUITY_STATISTICS });
  };

  const setStakingQueryStatus = (data: CommonQueryStatusData | null): void => {
    set(stakingQueryStatus, data);
  };

  return {
    balances,
    fetchBalances,
    fetchPools,
    fetchStaking,
    fetchStatistics,
    reset,
    setStakingQueryStatus,
    staking,
    stakingPools,
    stakingQueryStatus,
    statistics,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useLiquityStore, import.meta.hot));
