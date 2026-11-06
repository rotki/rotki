import { useFailureSlot } from '@/modules/shell/components/named-failure';

/**
 * Where actions started from the history events (the selection toolbar, a row, its menu, the
 * duplicate filter chip) leave a failure for the table to name.
 *
 * @remarks
 * Shared, because those actions run in composables that do not own the table. Each action clears it
 * as it starts, so a strip never outlives the next attempt.
 */
export const useHistoryEventsActionFailure = createSharedComposable(useFailureSlot);
