import type { StateHandler } from '../interfaces';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';

export function createHistoricalBalanceProcessingCompletedHandler(): StateHandler {
  const { notifyHistoricalBalanceProcessingCompleted } = useHistoricalBalanceProcessingStore();
  return createStateHandler(() => notifyHistoricalBalanceProcessingCompleted());
}
