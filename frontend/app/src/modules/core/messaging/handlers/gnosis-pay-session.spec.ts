import { beforeEach, describe, expect, it } from 'vitest';
import { createGnosisPaySessionHandler } from '@/modules/core/messaging/handlers/gnosis-pay-session';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

describe('createGnosisPaySessionHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should raise the expired-session row and create no notification', async () => {
    const handler = createGnosisPaySessionHandler();

    const result = await handler.handle({ error: 'session key expired' });

    expect(result).toBeNull();
    expect(useRaisedConditionsStore().conditions).toEqual([{ kind: RaisedConditionKind.GNOSIS_PAY_SESSION }]);
  });
});
