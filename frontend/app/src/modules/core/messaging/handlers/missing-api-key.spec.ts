import { beforeEach, describe, expect, it } from 'vitest';
import { createMissingApiKeyHandler } from '@/modules/core/messaging/handlers/missing-api-key';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

describe('createMissingApiKeyHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should raise a row for the service and create no notification', async () => {
    const handler = createMissingApiKeyHandler();

    const result = await handler.handle({ location: 'arbitrum_one', service: 'thegraph' });

    expect(result).toBeNull();
    expect(useRaisedConditionsStore().conditions).toEqual([
      { kind: RaisedConditionKind.MISSING_API_KEY, location: 'arbitrum_one', service: 'thegraph' },
    ]);
  });

  it('should keep one row per service across repeated reports', async () => {
    const handler = createMissingApiKeyHandler();

    await handler.handle({ service: 'etherscan' });
    await handler.handle({ service: 'blockscout' });
    await handler.handle({ service: 'etherscan' });

    expect(useRaisedConditionsStore().conditions.map(condition => condition.kind === RaisedConditionKind.MISSING_API_KEY && condition.service))
      .toEqual(['etherscan', 'blockscout']);
  });
});
