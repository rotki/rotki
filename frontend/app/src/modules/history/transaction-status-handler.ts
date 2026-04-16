import type { StateHandler } from '@/modules/core/messaging/interfaces';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';

export function createTransactionStatusHandler(): StateHandler {
  // Capture store method at handler creation time (in setup context)
  const { setUnifiedTxQueryStatus } = useTxQueryStatusStore();

  return createStateHandler((data) => {
    setUnifiedTxQueryStatus(data);
  });
}
