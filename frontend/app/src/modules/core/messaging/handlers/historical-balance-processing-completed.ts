import type { StateHandler } from '../interfaces';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';

export function createHistoricalBalanceProcessingCompletedHandler(): StateHandler {
  const { notifyHistoricalBalanceProcessingCompleted } = useDataIssuesInboxStore();
  return createStateHandler(() => notifyHistoricalBalanceProcessingCompleted());
}
