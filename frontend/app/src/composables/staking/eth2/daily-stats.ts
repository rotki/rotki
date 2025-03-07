import type { TaskMeta } from '@/types/task';
import type { Eth2DailyStats, Eth2DailyStatsPayload, EthStakingDailyStatData } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef, Ref } from 'vue';
import { useEth2Api } from '@/composables/api/staking/eth2';
import { usePremium } from '@/composables/premium';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';
import { useNotificationsStore } from '@/store/notifications';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useTaskStore } from '@/store/tasks';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { omit } from 'es-toolkit';

interface UseEthStakingDailyStatsReturn {
  pagination: Ref<Eth2DailyStatsPayload>;
  dailyStats: ComputedRef<EthStakingDailyStatData>;
  dailyStatsLoading: Ref<boolean>;
  refresh: () => Promise<void>;
  refreshStats: (userInitiated: boolean) => Promise<void>;
  syncStakingStats: (userInitiated?: boolean) => Promise<boolean>;
}

export function useEth2DailyStats(): UseEthStakingDailyStatsReturn {
  const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());
  const defaultPagination = (): Eth2DailyStatsPayload => ({
    ascending: [false],
    limit: get(itemsPerPage),
    offset: 0,
    orderByAttributes: ['timestamp'],
  });

  const pagination = ref<Eth2DailyStatsPayload>(defaultPagination());

  const premium = usePremium();
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const api = useEth2Api();

  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());

  const syncStakingStats = async (userInitiated = false): Promise<boolean> => {
    if (!get(premium))
      return false;

    const taskType = TaskType.STAKING_ETH2_STATS;

    const { fetchDisabled, setStatus } = useStatusUpdater(Section.STAKING_ETH2_STATS);

    if (fetchDisabled(userInitiated))
      return false;

    const defaults: Eth2DailyStatsPayload = {
      ascending: [false],
      limit: 0,
      offset: 0,
      onlyCache: false,
      orderByAttributes: ['timestamp'],
    };

    try {
      setStatus(userInitiated ? Status.REFRESHING : Status.LOADING);
      const { taskId } = await api.refreshStakingStats(defaults);

      const taskMeta: TaskMeta = {
        description: t('actions.eth2_staking_stats.task.description'),
        title: t('actions.eth2_staking_stats.task.title'),
      };

      await awaitTask<Eth2DailyStats, TaskMeta>(taskId, taskType, taskMeta, true);
      setStatus(Status.LOADED);
      return true;
    }
    catch (error: any) {
      setStatus(Status.NONE);

      if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.eth2_staking_stats.error.message', {
            message: error.message,
          }),
          title: t('actions.eth2_staking_stats.error.title'),
        });
      }
    }

    return false;
  };

  const fetchStakingStats = async (payload: MaybeRef<Eth2DailyStatsPayload>): Promise<Eth2DailyStats> => {
    assert(get(premium));

    return api.fetchStakingStats({
      ...get(payload),
      onlyCache: true,
    });
  };

  const {
    execute,
    isLoading: dailyStatsLoading,
    state,
  } = useAsyncState<Eth2DailyStats, MaybeRef<Eth2DailyStatsPayload>[]>(
    fetchStakingStats,
    {
      entries: [],
      entriesFound: 0,
      entriesTotal: 0,
      sumPnl: Zero,
    },
    {
      delay: 0,
      immediate: false,
      resetOnExecute: false,
    },
  );

  const dailyStats = computed<EthStakingDailyStatData>(() => {
    const dailyStats = get(state);
    const validators = get(ethStakingValidators);
    return {
      ...omit(dailyStats, ['entries']),
      entries: dailyStats.entries.map((stat) => {
        const ownershipPercentage = validators.find(({ index }) => index === stat.validatorIndex)
          ?.ownershipPercentage;
        return {
          ...stat,
          ownershipPercentage,
        };
      }),
    };
  });

  const fetchDailyStats = async (payload: Eth2DailyStatsPayload): Promise<void> => {
    await execute(0, payload);
  };

  async function refresh(): Promise<void> {
    // We unref here to make sure that we use the latest pagination
    await fetchDailyStats(get(pagination));
  }

  async function refreshStats(userInitiated: boolean): Promise<void> {
    await refresh();
    const success = await syncStakingStats(userInitiated);
    if (success)
      await refresh();
  }

  watch(pagination, async pagination => fetchDailyStats(pagination));

  return {
    dailyStats,
    dailyStatsLoading,
    pagination,
    refresh,
    refreshStats,
    syncStakingStats,
  };
}
