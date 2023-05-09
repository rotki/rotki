import {
  type Eth2DailyStats,
  type Eth2DailyStatsPayload
} from '@rotki/common/lib/staking/eth2';
import { type MaybeRef } from '@vueuse/core';

export const useEth2DailyStats = () => {
  const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());
  const defaultPagination = (): Eth2DailyStatsPayload => ({
    limit: get(itemsPerPage),
    offset: 0,
    orderByAttributes: ['timestamp'],
    ascending: [false]
  });

  const pagination: Ref<Eth2DailyStatsPayload> = ref(defaultPagination());

  const { fetchStakingStats, syncStakingStats } = useEth2StakingStore();

  const {
    state: dailyStats,
    execute,
    isLoading: dailyStatsLoading
  } = useAsyncState<Eth2DailyStats, MaybeRef<Eth2DailyStatsPayload>[]>(
    fetchStakingStats,
    {
      entries: [],
      entriesFound: 0,
      entriesTotal: 0,
      sumPnl: zeroBalance()
    },
    {
      immediate: false,
      resetOnExecute: false,
      delay: 0
    }
  );

  const fetchDailyStats = async (
    payload: Eth2DailyStatsPayload
  ): Promise<void> => {
    await execute(0, payload);
  };

  watch(pagination, pagination => fetchDailyStats(pagination));

  return {
    pagination,
    dailyStats,
    dailyStatsLoading,
    fetchDailyStats,
    syncStakingStats
  };
};
