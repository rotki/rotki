import {
  LiquityBalancesWithCollateralInfo,
  LiquityPoolDetails,
  LiquityStakingDetails,
  LiquityStatistics,
} from '@rotki/common';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import type { TaskMeta } from '@/types/task';
import type { OnError } from '@/types/fetch';

const defaultBalances = (): LiquityBalancesWithCollateralInfo => ({ balances: {}, totalCollateralRatio: null });

export const useLiquityStore = defineStore('defi/liquity', () => {
  const balances = ref<LiquityBalancesWithCollateralInfo>(defaultBalances());
  const staking = ref<LiquityStakingDetails>({});
  const stakingPools = ref<LiquityPoolDetails>({});
  const statistics = ref<LiquityStatistics | null>(null);

  const isPremium = usePremium();
  const { activeModules } = useModules();
  const { t } = useI18n();
  const {
    fetchLiquityStakingPools,
    fetchLiquityBalances,
    fetchLiquityStaking,
    fetchLiquityStatistics,
  } = useLiquityApi();

  const fetchPools = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.liquity_pools.task.title'),
    };

    const onError: OnError = {
      title: t('actions.defi.liquity_pools.error.title'),
      error: message =>
        t('actions.defi.liquity_pools.error.description', {
          message,
        }),
    };

    await fetchDataAsync({
      task: {
        type: TaskType.LIQUITY_STAKING_POOLS,
        section: Section.DEFI_LIQUITY_STAKING_POOLS,
        meta,
        query: async () => await fetchLiquityStakingPools(),
        parser: result => LiquityPoolDetails.parse(result),
        onError,
      },
      state: {
        isPremium,
        activeModules,
      },
      requires: {
        premium: true,
        module: Module.LIQUITY,
      },
      refresh,
    }, stakingPools);
  };

  const fetchBalances = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.liquity.task.title').toString(),
    };

    const onError: OnError = {
      title: t('actions.defi.liquity_balances.error.title').toString(),
      error: message =>
        t('actions.defi.liquity_balances.error.description', {
          message,
        }).toString(),
    };

    await fetchDataAsync({
      task: {
        type: TaskType.LIQUITY_BALANCES,
        section: Section.DEFI_LIQUITY_BALANCES,
        meta,
        query: async () => await fetchLiquityBalances(),
        parser: result => LiquityBalancesWithCollateralInfo.parse(result),
        onError,
      },
      state: {
        isPremium,
        activeModules,
      },
      requires: {
        premium: false,
        module: Module.LIQUITY,
      },
      refresh,
    }, balances);
  };

  const fetchStaking = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.liquity_staking.task.title').toString(),
    };

    const onError: OnError = {
      title: t('actions.defi.liquity_staking.error.title').toString(),
      error: message =>
        t('actions.defi.liquity_staking.error.description', {
          message,
        }).toString(),
    };

    await fetchDataAsync({
      task: {
        type: TaskType.LIQUITY_STAKING,
        section: Section.DEFI_LIQUITY_STAKING,
        meta,
        query: async () => await fetchLiquityStaking(),
        parser: result => LiquityStakingDetails.parse(result),
        onError,
      },
      state: {
        isPremium,
        activeModules,
      },
      requires: {
        premium: true,
        module: Module.LIQUITY,
      },
      refresh,
    }, staking);
  };

  const fetchStatistics = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.liquity_statistics.task.title'),
    };

    const onError: OnError = {
      title: t('actions.defi.liquity_statistics.error.title'),
      error: message =>
        t('actions.defi.liquity_statistics.error.description', {
          message,
        }),
    };

    await fetchDataAsync({
      task: {
        type: TaskType.LIQUITY_STATISTICS,
        section: Section.DEFI_LIQUITY_STATISTICS,
        meta,
        query: async () => await fetchLiquityStatistics(),
        parser: result => LiquityStatistics.parse(result),
        onError,
      },
      state: {
        isPremium,
        activeModules,
      },
      requires: {
        premium: true,
        module: Module.LIQUITY,
      },
      refresh,
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

  return {
    balances,
    staking,
    stakingPools,
    statistics,
    fetchBalances,
    fetchStaking,
    fetchPools,
    fetchStatistics,
    reset,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useLiquityStore, import.meta.hot));
