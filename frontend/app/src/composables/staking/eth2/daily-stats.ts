import { type MaybeRef, objectOmit } from '@vueuse/core';
import { TaskType } from '@/types/task-type';
import { Section, Status } from '@/types/status';
import type { Eth2DailyStats, Eth2DailyStatsPayload, EthStakingDailyStatData } from '@rotki/common';
import type { TaskMeta } from '@/types/task';

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
    limit: get(itemsPerPage),
    offset: 0,
    orderByAttributes: ['timestamp'],
    ascending: [false],
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
      limit: 0,
      offset: 0,
      ascending: [false],
      orderByAttributes: ['timestamp'],
      onlyCache: false,
    };

    try {
      setStatus(userInitiated ? Status.REFRESHING : Status.LOADING);
      const { taskId } = await api.refreshStakingStats(defaults);

      const taskMeta: TaskMeta = {
        title: t('actions.eth2_staking_stats.task.title'),
        description: t('actions.eth2_staking_stats.task.description'),
      };

      await awaitTask<Eth2DailyStats, TaskMeta>(taskId, taskType, taskMeta, true);
      setStatus(Status.LOADED);
      return true;
    }
    catch (error: any) {
      setStatus(Status.NONE);

      if (!isTaskCancelled(error)) {
        notify({
          title: t('actions.eth2_staking_stats.error.title'),
          message: t('actions.eth2_staking_stats.error.message', {
            message: error.message,
          }),
          display: true,
        });
      }
    }

    return false;
  };

  const fetchStakingStats = async (payload: MaybeRef<Eth2DailyStatsPayload>): Promise<Eth2DailyStats> => {
    assert(get(premium));

    return await api.fetchStakingStats({
      ...get(payload),
      onlyCache: true,
    });
  };

  const {
    state,
    execute,
    isLoading: dailyStatsLoading,
  } = useAsyncState<Eth2DailyStats, MaybeRef<Eth2DailyStatsPayload>[]>(
    fetchStakingStats,
    {
      entries: [],
      entriesFound: 0,
      entriesTotal: 0,
      sumPnl: Zero,
    },
    {
      immediate: false,
      resetOnExecute: false,
      delay: 0,
    },
  );

  const dailyStats = computed<EthStakingDailyStatData>(() => {
    const dailyStats = get(state);
    const validators = get(ethStakingValidators);
    return {
      ...objectOmit(dailyStats, ['entries']),
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

  watch(pagination, pagination => fetchDailyStats(pagination));

  return {
    pagination,
    dailyStats,
    dailyStatsLoading,
    refresh,
    refreshStats,
    syncStakingStats,
  };
}
