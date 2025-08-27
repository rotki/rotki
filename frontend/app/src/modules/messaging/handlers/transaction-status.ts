import type { StateHandler } from '../interfaces';
import { createStateHandler } from '@/modules/messaging/utils';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';

export function createTransactionStatusHandler(): StateHandler {
  return createStateHandler((data) => {
    const { setUnifiedTxQueryStatus } = useTxQueryStatusStore();
    setUnifiedTxQueryStatus(data);
  });
}
