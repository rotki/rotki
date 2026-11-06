import type { ComputedRef } from 'vue';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import type { HistoryEventsTableEmitFn, HistoryEventUnlinkPayload } from '@/modules/history/events/types';
import { useAssetMovementMatchingApi } from '@/modules/history/api/events/use-asset-movement-matching-api';
import { useBridgeMatchingApi } from '@/modules/history/api/events/use-bridge-matching-api';
import { getMatchedMovementIgnoreIds, isAssetMovementEvent } from '@/modules/history/event-utils';
import { useCompleteEvents } from '@/modules/history/events/use-complete-events';
import { useHistoryEventsActionFailure } from '@/modules/history/events/use-history-events-action-failure';
import { useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { EditKind } from '@/modules/task-center/core/rerun/policy';
import { taskCenterBus } from '@/modules/task-center/events/task-center-bus';

interface UseMatchedEventsUnlinkReturn {
  /** Unlinks a match the row already asked about; a failure is named above the table. */
  unlink: (payload: HistoryEventUnlinkPayload) => Promise<void>;
  /** Unlinks the matched asset movement of a group, from its expanded header, which already asked. */
  unlinkGroup: (groupId: string) => Promise<void>;
}

/**
 * Undoes a match from the history events list. Asset movements and bridge transfers are linked
 * through different endpoints, and each keeps its own unmatched list that has to be refreshed.
 */
export function useMatchedEventsUnlink(
  completeEventsMapped: ComputedRef<Record<string, HistoryEventRow[]>>,
  emit: HistoryEventsTableEmitFn,
): UseMatchedEventsUnlinkReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { run: runAction } = useHistoryEventsActionFailure();
  const { getGroupEvents } = useCompleteEvents(completeEventsMapped);
  const { matchAssetMovements, unlinkAssetMovement } = useAssetMovementMatchingApi();
  const { matchBridgeTransactions, unlinkBridgeTransaction } = useBridgeMatchingApi();
  const { refreshUnmatchedAssetMovements } = useUnmatchedAssetMovements();
  const { refreshUnmatchedBridgeTransactions } = useUnmatchedBridgeTransactions();

  /**
   * Unlinking alone does not stick: a match the automatic matcher made is deterministic, so
   * returning the legs to the unmatched pool restores exactly the state it acted on and the next
   * run links them straight back. Ignoring them is what makes the undo durable, and the ignored
   * tab of the matching dialog is where the user restores or matches them by hand.
   *
   * Ignoring is matching with no counterpart, and a later match clears the ignore itself. The
   * calls are sequential rather than concurrent because they all write the same table, and they
   * follow the unlink so that a failed unlink ignores nothing.
   */
  async function unlinkMatch(payload: HistoryEventUnlinkPayload): Promise<void> {
    if (payload.type === 'bridge') {
      await unlinkBridgeTransaction(payload.identifier);
      for (const identifier of payload.ignoredIdentifiers)
        await matchBridgeTransactions(identifier);

      await refreshUnmatchedBridgeTransactions();
    }
    else {
      await unlinkAssetMovement(payload.identifier);
      for (const identifier of payload.ignoredIdentifiers)
        await matchAssetMovements(identifier);

      await refreshUnmatchedAssetMovements();
    }
  }

  async function unlink(payload: HistoryEventUnlinkPayload): Promise<void> {
    const title = payload.type === 'bridge' ? t('transactions.events.unlink_bridge_error') : t('transactions.events.unlink_error');
    await runAction(title, async () => {
      await unlinkMatch(payload);
      emit('refresh');
      taskCenterBus.emit('event:mutated', { kind: EditKind.EVENT_UNLINKED });
    });
  }

  async function unlinkGroup(groupId: string): Promise<void> {
    const events = getGroupEvents(groupId);
    const event = events.find(item => isAssetMovementEvent(item) && item.eventSubtype !== 'fee' && !!item.actualGroupIdentifier);
    if (event) {
      await unlink({
        identifier: event.identifier,
        ignoredIdentifiers: getMatchedMovementIgnoreIds(events),
        type: 'asset-movement',
      });
    }
  }

  return {
    unlink,
    unlinkGroup,
  };
}
