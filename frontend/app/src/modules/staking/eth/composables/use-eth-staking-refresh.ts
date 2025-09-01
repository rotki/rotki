import type { ComputedRef, Ref } from 'vue';
import { Blockchain } from '@rotki/common';
import dayjs from 'dayjs';
import { useEthStaking } from '@/composables/blockchain/accounts/staking';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';
import { useSessionAuthStore } from '@/store/session/auth';
import { useStatusStore } from '@/store/status';
import { useTaskStore } from '@/store/tasks';
import { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

interface RefreshCallbacks {
  getPerformance: () => { entriesTotal: number };
  refreshPerformance: (userInitiated: boolean) => Promise<void>;
  setTotal: () => void;
}

interface UseEthStakingRefreshReturn {
  blockProductionLoading: ComputedRef<boolean>;
  lastRefresh: Ref<number>;
  performanceRefreshing: ComputedRef<boolean>;
  refresh: (userInitiated?: boolean) => Promise<void>;
  refreshing: ComputedRef<boolean>;
}

export function useEthStakingRefresh(callbacks: RefreshCallbacks): UseEthStakingRefreshReturn {
  const performanceSection = Section.STAKING_ETH2;

  const { username } = storeToRefs(useSessionAuthStore());
  const { isLoading } = useStatusStore();
  const { useIsTaskRunning } = useTaskStore();
  const { stakingValidatorsLimits } = storeToRefs(useBlockchainValidatorsStore());
  const { fetchEthStakingValidators } = useEthStaking();
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const { isFirstLoad } = useStatusUpdater(performanceSection);

  function createLastRefreshStorage(username: string): Ref<number> {
    return useSessionStorage(`rotki.staking.last_refresh.${username}`, 0);
  }

  const lastRefresh = createLastRefreshStorage(get(username));

  // Loading states
  const performanceRefreshing = isLoading(performanceSection);
  const blockProductionLoading = useIsTaskRunning(TaskType.QUERY_ONLINE_EVENTS, {
    queryType: OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
  });

  const refreshing = logicOr(
    performanceRefreshing,
    isLoading(Section.BLOCKCHAIN, Blockchain.ETH2),
    blockProductionLoading,
  );

  async function refresh(userInitiated = false): Promise<void> {
    const refreshValidators = async (userInitiated: boolean): Promise<void> => {
      await fetchBlockchainBalances({
        blockchain: Blockchain.ETH2,
        ignoreCache: userInitiated || isFirstLoad(),
      });
      await fetchEthStakingValidators();
    };

    const updatePerformance = async (userInitiated = false): Promise<void> => {
      await callbacks.refreshPerformance(userInitiated);
      // if the number of validators is bigger than the total entries in performance
      // force a refresh of performance to pick the missing performance entries.
      const totalValidators = get(stakingValidatorsLimits)?.total ?? 0;
      const performance = callbacks.getPerformance();
      const totalPerformanceEntries = performance.entriesTotal ?? 0;
      if (totalValidators > totalPerformanceEntries) {
        logger.log(`forcing refresh validators: ${totalValidators}/performance: ${totalPerformanceEntries}`);
        await callbacks.refreshPerformance(true);
      }
    };

    await refreshValidators(userInitiated);
    callbacks.setTotal();

    await updatePerformance(userInitiated);
    set(lastRefresh, dayjs().unix());
  }

  return {
    blockProductionLoading,
    lastRefresh,
    performanceRefreshing,
    refresh,
    refreshing,
  };
}
