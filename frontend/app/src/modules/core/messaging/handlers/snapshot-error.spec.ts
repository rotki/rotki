import { Severity } from '@rotki/common';
import { mockT } from '@test/i18n';
import { describe, expect, it } from 'vitest';
import { createSnapshotErrorHandler } from '@/modules/core/messaging/handlers/snapshot-error';

const failure = { error: 'Could not reach kraken', location: 'kraken' };

describe('createSnapshotErrorHandler', () => {
  it('should report a failed snapshot for its location', async () => {
    const result = await createSnapshotErrorHandler(mockT).handle(failure);

    expect(result).toMatchObject({
      message: 'notification_messages.snapshot_failed.message::Could not reach kraken, kraken',
      severity: Severity.ERROR,
    });
  });

  it('should say how many times a failure the backend held was sent', async () => {
    const result = await createSnapshotErrorHandler(mockT).handle(failure, { count: 4 });

    expect(result.message).toBe(
      'notification_messages.repeated::4, notification_messages.snapshot_failed.message::Could not reach kraken, kraken',
    );
  });
});
