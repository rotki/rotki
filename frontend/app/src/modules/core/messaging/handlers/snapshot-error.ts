import type { MessageHandler } from '../interfaces';
import type { BalanceSnapshotError } from '@/modules/core/messaging/types';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { BALANCE_SNAPSHOT } from '@/modules/core/notifications/problems/backend-problem-tree';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';

/**
 * Files a balance snapshot that failed to save as a backend problem, under the location it failed
 * at. It never creates a notification.
 *
 * @remarks
 * Each failed snapshot is its own item, identified by when it was sent: two failures are two
 * snapshots the user is missing, not one problem repeating.
 */
export function createSnapshotErrorHandler(t: ReturnType<typeof useI18n>['t']): MessageHandler<BalanceSnapshotError> {
  const { record } = useBackendProblemsStore();

  return createConditionalHandler<BalanceSnapshotError>((data, { count, lastSent }) => {
    const at = lastSent ?? new Date();
    record({
      at,
      count,
      identity: String(at.getTime()),
      source: {
        fields: { error: data.error },
        key: BALANCE_SNAPSHOT,
        subject: data.location,
        value: t('notification_messages.snapshot_failed.message', data),
        verbosity: 'error',
      },
    });
    return null;
  });
}
