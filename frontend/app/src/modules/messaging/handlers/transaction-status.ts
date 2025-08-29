import type { StateHandler } from '../interfaces';
import { createStateHandler } from '@/modules/messaging/utils';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';

export function createTransactionStatusHandler(): StateHandler {
  // Capture store method at handler creation time (in setup context)
  const { setUnifiedTxQueryStatus } = useTxQueryStatusStore();

  return createStateHandler((data) => {
    setUnifiedTxQueryStatus(data);
  });
}
