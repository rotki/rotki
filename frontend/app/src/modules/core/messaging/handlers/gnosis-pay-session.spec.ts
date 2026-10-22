import { beforeEach, describe, expect, it } from 'vitest';
import { createGnosisPaySessionHandler } from '@/modules/core/messaging/handlers/gnosis-pay-session';
import { RaisedConditionKind, SessionCause, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

describe('createGnosisPaySessionHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should raise the expired-session row and create no notification', async () => {
    const handler = createGnosisPaySessionHandler();

    const result = await handler.handle({ error: 'session key expired', reason: 'expired', reminder: false });

    expect(result).toBeNull();
    expect(useRaisedConditionsStore().conditions).toEqual([
      { cause: SessionCause.EXPIRED, kind: RaisedConditionKind.GNOSIS_PAY_SESSION },
    ]);
  });

  it('should raise the row as not connected for a user who never signed in', async () => {
    const handler = createGnosisPaySessionHandler();

    await handler.handle({ error: 'not connected', reason: 'not_connected', reminder: true });

    expect(useRaisedConditionsStore().conditions).toEqual([
      { cause: SessionCause.NOT_CONNECTED, kind: RaisedConditionKind.GNOSIS_PAY_SESSION },
    ]);
  });

  it('should keep one row when every redecode repeats the reminder', async () => {
    const handler = createGnosisPaySessionHandler();

    await handler.handle({ error: 'expired', reason: 'expired', reminder: false });
    await handler.handle({ error: 'expired', reason: 'expired', reminder: true });
    await handler.handle({ error: 'expired', reason: 'expired', reminder: true });

    expect(useRaisedConditionsStore().conditions).toHaveLength(1);
  });
});
