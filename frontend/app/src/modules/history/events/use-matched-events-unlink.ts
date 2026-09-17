import type { ComputedRef } from 'vue';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import type { HistoryEventsTableEmitFn, HistoryEventUnlinkPayload } from '@/modules/history/events/types';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useAssetMovementMatchingApi } from '@/modules/history/api/events/use-asset-movement-matching-api';
import { useBridgeMatchingApi } from '@/modules/history/api/events/use-bridge-matching-api';
import { isAssetMovementEvent } from '@/modules/history/event-utils';
import { useCompleteEvents } from '@/modules/history/events/use-complete-events';
import { useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { EditKind } from '@/modules/task-center/core/rerun/policy';
import { taskCenterBus } from '@/modules/task-center/events/task-center-bus';

interface UseMatchedEventsUnlinkReturn {
  confirmUnlink: (payload: HistoryEventUnlinkPayload) => void;
  /** Unlinks the matched asset movement of a group, from its expanded header. */
  unlinkGroup: (groupId: string) => void;
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

  const { notifyError } = useNotifications();
  const { show } = useConfirmStore();
  const { getGroupEvents } = useCompleteEvents(completeEventsMapped);
  const { unlinkAssetMovement } = useAssetMovementMatchingApi();
  const { unlinkBridgeTransaction } = useBridgeMatchingApi();
  const { refreshUnmatchedAssetMovements } = useUnmatchedAssetMovements();
  const { refreshUnmatchedBridgeTransactions } = useUnmatchedBridgeTransactions();

  async function unlink({ identifier, type }: HistoryEventUnlinkPayload): Promise<void> {
    if (type === 'bridge') {
      await unlinkBridgeTransaction(identifier);
      await refreshUnmatchedBridgeTransactions();
    }
    else {
      await unlinkAssetMovement(identifier);
      await refreshUnmatchedAssetMovements();
    }
  }

  async function onConfirmUnlink(payload: HistoryEventUnlinkPayload): Promise<void> {
    try {
      await unlink(payload);
      emit('refresh');
      taskCenterBus.emit('event:mutated', { kind: EditKind.EVENT_UNLINKED });
    }
    catch (error: unknown) {
      notifyError(
        payload.type === 'bridge' ? t('transactions.events.unlink_bridge_error') : t('transactions.events.unlink_error'),
        getErrorMessage(error),
      );
    }
  }

  function confirmUnlink(payload: HistoryEventUnlinkPayload): void {
    show({
      message: payload.type === 'bridge'
        ? t('transactions.events.confirmation.unlink.bridge_message')
        : t('transactions.events.confirmation.unlink.message'),
      primaryAction: t('common.actions.confirm'),
      title: t('transactions.events.confirmation.unlink.title'),
    }, async () => onConfirmUnlink(payload));
  }

  function unlinkGroup(groupId: string): void {
    const events = getGroupEvents(groupId);
    const event = events.find(item => isAssetMovementEvent(item) && item.eventSubtype !== 'fee' && !!item.actualGroupIdentifier);
    if (event)
      confirmUnlink({ identifier: event.identifier, type: 'asset-movement' });
  }

  return {
    confirmUnlink,
    unlinkGroup,
  };
}
