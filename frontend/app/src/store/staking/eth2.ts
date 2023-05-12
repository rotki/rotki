import {
  type Eth2DailyStats,
  type Eth2DailyStatsPayload,
  Eth2Details,
  type Eth2StakingRewards,
  type EthStakingPayload,
  type EthStakingRewardsPayload
} from '@rotki/common/lib/staking/eth2';
import { type MaybeRef } from '@vueuse/core';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const useEth2StakingStore = defineStore('staking/eth2', () => {
  const details: Ref<Eth2Details> = ref([]);

  const premium = usePremium();
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t, tc } = useI18n();

  const api = useEth2Api();

  const fetchStakingDetails = async (
    refresh = false,
    payload: EthStakingPayload = {}
  ): Promise<void> => {
    if (!get(premium)) {
      return;
    }

    const { setStatus, resetStatus, fetchDisabled } = useStatusUpdater(
      Section.STAKING_ETH2
    );

    const ignoreCache = !fetchDisabled(refresh);

    setStatus(refresh ? Status.REFRESHING : Status.LOADING);

    try {
      const taskType = TaskType.STAKING_ETH2;
      const { taskId } = await api.fetchStakingDetails({
        ...payload,
        ignoreCache
      });
      const { result } = await awaitTask<Eth2Details, TaskMeta>(
        taskId,
        taskType,
        {
          title: tc('actions.staking.eth2.task.title')
        }
      );

      set(details, Eth2Details.parse(result));
    } catch (e: any) {
      logger.error(e);
      notify({
        title: tc('actions.staking.eth2.error.title'),
        message: tc('actions.staking.eth2.error.description', undefined, {
          error: e.message
        }),
        display: true
      });
      resetStatus();
    }
    setStatus(Status.LOADED);
  };

  const fetchStakingRewards = async (
    payload: MaybeRef<EthStakingRewardsPayload> = {}
  ): Promise<Eth2StakingRewards> => api.fetchStakingDetailRewards(get(payload));

  const syncStakingStats = async (userInitiated = false): Promise<boolean> => {
    if (!get(premium)) {
      return false;
    }
    const taskType = TaskType.STAKING_ETH2_STATS;

    const { fetchDisabled, setStatus } = useStatusUpdater(
      Section.STAKING_ETH2_STATS
    );

    if (fetchDisabled(userInitiated)) {
      return false;
    }

    const defaults: Eth2DailyStatsPayload = {
      limit: 0,
      offset: 0,
      ascending: [false],
      orderByAttributes: ['timestamp'],
      onlyCache: false
    };

    try {
      const { taskId } = await api.refreshStakingStats(defaults);

      const taskMeta: TaskMeta = {
        title: t('actions.eth2_staking_stats.task.title').toString(),
        description: t('actions.eth2_staking_stats.task.description').toString()
      };

      await awaitTask<Eth2DailyStats, TaskMeta>(
        taskId,
        taskType,
        taskMeta,
        true
      );
      setStatus(Status.LOADED);
      return true;
    } catch (e: any) {
      setStatus(Status.NONE);
      notify({
        title: t('actions.eth2_staking_stats.error.title').toString(),
        message: t('actions.eth2_staking_stats.error.message', {
          message: e.message
        }).toString(),
        display: true
      });
    }

    return false;
  };

  const fetchStakingStats = async (
    payload: MaybeRef<Eth2DailyStatsPayload>
  ): Promise<Eth2DailyStats> => {
    assert(get(premium));

    return await api.fetchStakingStats({
      ...get(payload),
      onlyCache: true
    });
  };

  return {
    details,
    fetchStakingDetails,
    fetchStakingRewards,
    fetchStakingStats,
    syncStakingStats
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useEth2StakingStore, import.meta.hot));
}
