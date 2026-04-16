import type { StateHandler } from '../interfaces';
import { useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';
import { createStateHandler } from '@/modules/messaging/utils';

export function createTransactionStatusHandler(): StateHandler {
  // Capture store method at handler creation time (in setup context)
  const { setUnifiedTxQueryStatus } = useTxQueryStatusStore();

  return createStateHandler((data) => {
    setUnifiedTxQueryStatus(data);
  });
}
