import type { MessageHandler } from '../interfaces';
import type { UnmatchedAssetMovementsData } from '@/modules/core/messaging/types';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';

/**
 * Re-reads the unmatched asset movements the action center row counts, once the backend reports
 * that matching changed them.
 *
 * @remarks
 * Creates no notification. The message carries a count, but the row counts the list itself, so the
 * list is what gets refreshed.
 */
export function createUnmatchedAssetMovementsHandler(): MessageHandler<UnmatchedAssetMovementsData> {
  const { fetchUnmatchedAssetMovements } = useUnmatchedAssetMovements();

  return createConditionalHandler<UnmatchedAssetMovementsData>(async () => {
    await fetchUnmatchedAssetMovements();
    return null;
  });
}
