import { mockT } from '@test/i18n';
import { createCustomPinia } from '@test/utils/create-pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { createSnapshotErrorHandler } from '@/modules/core/messaging/handlers/snapshot-error';
import { BALANCE_SNAPSHOT } from '@/modules/core/notifications/problems/backend-problem-tree';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';

const failure = { error: 'Could not reach kraken', location: 'kraken' };

describe('createSnapshotErrorHandler', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  it('should file a failed snapshot under its location, without a notification', async () => {
    const result = await createSnapshotErrorHandler(mockT).handle(failure);

    expect(result).toBeNull();
    expect(get(storeToRefs(useBackendProblemsStore()).problems)).toMatchObject([{
      items: [{
        repeats: 1,
        source: {
          fields: { error: 'Could not reach kraken' },
          value: 'notification_messages.snapshot_failed.message::Could not reach kraken, kraken',
        },
      }],
      key: BALANCE_SNAPSHOT,
      subject: 'kraken',
      verbosity: 'error',
    }]);
  });

  it('should keep each failed snapshot as its own item', async () => {
    const handler = createSnapshotErrorHandler(mockT);

    await handler.handle(failure, { count: 1, lastSent: new Date('2026-09-30T07:00:00Z') });
    await handler.handle(failure, { count: 1, lastSent: new Date('2026-09-30T08:00:00Z') });

    const [problem] = get(storeToRefs(useBackendProblemsStore()).problems);
    expect(problem.items).toHaveLength(2);
  });

  it('should count every send of a failure the backend held', async () => {
    await createSnapshotErrorHandler(mockT).handle(failure, { count: 4, lastSent: new Date('2026-09-30T07:00:00Z') });

    const [problem] = get(storeToRefs(useBackendProblemsStore()).problems);
    expect(problem.items).toMatchObject([{ repeats: 4 }]);
  });
});
