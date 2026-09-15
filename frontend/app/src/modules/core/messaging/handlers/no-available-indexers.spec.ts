import { beforeEach, describe, expect, it } from 'vitest';
import { createNoAvailableIndexersHandler } from '@/modules/core/messaging/handlers/no-available-indexers';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

describe('createNoAvailableIndexersHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should raise a row for the chain and create no notification', async () => {
    const handler = createNoAvailableIndexersHandler();

    const result = await handler.handle({ chain: 'optimism' });

    expect(result).toBeNull();
    expect(useRaisedConditionsStore().conditions).toEqual([
      { chain: 'optimism', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS, paidKeyRequired: false },
    ]);
  });

  it('should record a paid etherscan key as the way out when that is the reason given', async () => {
    const handler = createNoAvailableIndexersHandler();

    await handler.handle({ chain: 'base', reason: 'etherscan_paid_key_required' });

    expect(useRaisedConditionsStore().conditions).toEqual([
      { chain: 'base', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS, paidKeyRequired: true },
    ]);
  });

  it('should not read an unrecognised reason as a paid key requirement', async () => {
    const handler = createNoAvailableIndexersHandler();

    await handler.handle({ chain: 'base', reason: 'rate_limited' });

    expect(useRaisedConditionsStore().conditions).toEqual([
      { chain: 'base', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS, paidKeyRequired: false },
    ]);
  });

  it('should give each chain its own row', async () => {
    const handler = createNoAvailableIndexersHandler();

    await handler.handle({ chain: 'optimism' });
    await handler.handle({ chain: 'binance_sc' });

    expect(useRaisedConditionsStore().conditions).toHaveLength(2);
  });
});
