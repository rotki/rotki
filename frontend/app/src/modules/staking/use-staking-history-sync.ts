import type { ComputedRef } from 'vue';
import { Blockchain } from '@rotki/common';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryTransactions } from '@/modules/history/events/tx/use-history-transactions';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseStakingHistorySyncReturn {
  /** The synced chain's name, as the refresh menu describes the sync. */
  chainName: ComputedRef<string>;
  syncHistory: () => Promise<void>;
  syncingHistory: ComputedRef<boolean>;
}

/**
 * The full history sync a staking page offers in its refresh menu: the transactions of the
 * chain's accounts, exchanges and banks, decoded, after which the page's events section reads
 * its events again.
 *
 * @param reloadEvents - asks the page's events section to read its events again
 * @param chain - the chain the page's staking events come from
 */
export function useStakingHistorySync(
  reloadEvents: () => void,
  chain: string = Blockchain.ETH,
): UseStakingHistorySyncReturn {
  const { refreshTransactions } = useHistoryTransactions();
  const { useIsActive } = useTaskCenter();
  const { getChainName } = useSupportedChains();

  const syncingHistory = useIsActive(ActivityKind.HISTORY_SYNC);
  const chainName = computed<string>(() => getChainName(chain));

  async function syncHistory(): Promise<void> {
    await refreshTransactions({
      chains: [chain],
      disableEvmEvents: true,
      userInitiated: true,
    });
    reloadEvents();
  }

  return {
    chainName,
    syncHistory,
    syncingHistory,
  };
}
