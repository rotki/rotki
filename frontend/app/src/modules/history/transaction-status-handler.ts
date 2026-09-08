import type { StateHandler } from '@/modules/core/messaging/interfaces';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';

export function createTransactionStatusHandler(): StateHandler {
  const { setUnifiedTxQueryStatus } = useTxQueryStatusStore();

  return createStateHandler((data) => {
    setUnifiedTxQueryStatus(data);
  });
}
