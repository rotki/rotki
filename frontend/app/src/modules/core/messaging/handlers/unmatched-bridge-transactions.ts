import type { MessageHandler } from '../interfaces';
import type { UnmatchedBridgeTransactionsData } from '@/modules/core/messaging/types';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';

/**
 * Re-reads the unmatched bridge legs the action center row counts, once the backend reports that
 * matching changed them.
 *
 * @remarks
 * Creates no notification. The message carries a count, but the row counts the list itself, so the
 * list is what gets refreshed.
 */
export function createUnmatchedBridgeTransactionsHandler(): MessageHandler<UnmatchedBridgeTransactionsData> {
  const { fetchUnmatchedBridgeTransactions } = useUnmatchedBridgeTransactions();

  return createConditionalHandler<UnmatchedBridgeTransactionsData>(async () => {
    await fetchUnmatchedBridgeTransactions();
    return null;
  });
}
