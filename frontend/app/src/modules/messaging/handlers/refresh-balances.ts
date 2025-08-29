import type { StateHandler } from '../interfaces';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { createStateHandler } from '@/modules/messaging/utils';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

export function createRefreshBalancesHandler(): StateHandler {
  // Capture functions at handler creation time (in setup context)
  const { isTaskRunning } = useTaskStore();
  const { fetchBlockchainBalances } = useBlockchainBalances();

  return createStateHandler(async (data) => {
    const isDecoding = isTaskRunning(TaskType.TRANSACTIONS_DECODING);
    if (!isDecoding) {
      await fetchBlockchainBalances({
        blockchain: data.blockchain,
        ignoreCache: true,
      });
    }
  });
}
