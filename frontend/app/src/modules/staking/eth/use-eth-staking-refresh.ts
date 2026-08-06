import type { ComputedRef, Ref } from 'vue';
import { Blockchain } from '@rotki/common';
import dayjs from 'dayjs';
import { useEthStaking } from '@/modules/accounts/use-eth-staking';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { logger } from '@/modules/core/common/logging/logging';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';
import { ActivityPart } from '@/modules/task-center/core/types';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';

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
  const { username } = storeToRefs(useSessionAuthStore());
  const { stakingValidatorsLimits } = storeToRefs(useBlockchainValidatorsStore());
  const { fetchEthStakingValidators } = useEthStaking();
  const { fetchBlockchainBalances, refreshBlockchainBalances } = useBlockchainBalances();
  const { useIsActive, useWorkStatus, useIsActivePrefix } = useTaskCenter();

  const performanceStatus = useWorkStatus(ActivityKind.STAKING, ActivityPart.PERFORMANCE);

  // `isFirstLoad()` on the performance section is now the orchestrator's freshness ledger.
  function isFirstLoad(): boolean {
    return !get(performanceStatus).everCompleted;
  }

  function createLastRefreshStorage(username: string): Ref<number> {
    return useSessionStorage(`rotki.staking.last_refresh.${username}`, 0);
  }

  const lastRefresh = createLastRefreshStorage(get(username));

  // Loading states
  const performanceRefreshing = computed<boolean>(() => get(performanceStatus).active);
  const eth2Loading = useIsActivePrefix(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.ETH2);
  const blockProductionLoading = useIsActive(ActivityKind.ONLINE_EVENTS, OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS);

  const refreshing = logicOr(
    performanceRefreshing,
    eth2Loading,
    blockProductionLoading,
  );

  async function refresh(userInitiated = false): Promise<void> {
    const refreshValidators = async (userInitiated: boolean): Promise<void> => {
      const shouldRefresh = userInitiated || isFirstLoad();
      if (shouldRefresh) {
        await refreshBlockchainBalances({
          blockchain: Blockchain.ETH2,
        });
      }
      else {
        await fetchBlockchainBalances({
          blockchain: Blockchain.ETH2,
        });
      }
      await fetchEthStakingValidators({
        ignoreCache: userInitiated || isFirstLoad(),
      });
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
