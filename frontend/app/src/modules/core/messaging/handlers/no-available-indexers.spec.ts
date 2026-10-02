import { beforeEach, describe, expect, it } from 'vitest';
import { createNoAvailableIndexersHandler } from '@/modules/core/messaging/handlers/no-available-indexers';
import { NoIndexersCause, RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

describe('createNoAvailableIndexersHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should raise a row for the chain and create no notification', async () => {
    const handler = createNoAvailableIndexersHandler();

    const result = await handler.handle({ chain: 'optimism' });

    expect(result).toBeNull();
    expect(useRaisedConditionsStore().conditions).toEqual([
      { cause: NoIndexersCause.UNAVAILABLE, chain: 'optimism', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS },
    ]);
  });

  it.each([
    ['etherscan_paid_key_required', NoIndexersCause.PAID_ETHERSCAN_KEY],
    ['blockscout_or_paid_etherscan_key_required', NoIndexersCause.BLOCKSCOUT_OR_PAID_ETHERSCAN_KEY],
  ])('should record the cause of reason %s', async (reason, cause) => {
    const handler = createNoAvailableIndexersHandler();

    await handler.handle({ chain: 'base', reason });

    expect(useRaisedConditionsStore().conditions).toEqual([
      { cause, chain: 'base', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS },
    ]);
  });

  it('should not read an unrecognised reason as a key requirement', async () => {
    const handler = createNoAvailableIndexersHandler();

    await handler.handle({ chain: 'base', reason: 'rate_limited' });

    expect(useRaisedConditionsStore().conditions).toEqual([
      { cause: NoIndexersCause.UNAVAILABLE, chain: 'base', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS },
    ]);
  });

  it('should give each chain its own row', async () => {
    const handler = createNoAvailableIndexersHandler();

    await handler.handle({ chain: 'optimism' });
    await handler.handle({ chain: 'binance_sc' });

    expect(useRaisedConditionsStore().conditions).toHaveLength(2);
  });

  it('should raise nothing for an incomplete blockscout response, since the failed sync shows in the dock', async () => {
    const handler = createNoAvailableIndexersHandler();

    const result = await handler.handle({ chain: 'optimism', reason: 'blockscout_incomplete_response' });

    expect(result).toBeNull();
    expect(useRaisedConditionsStore().conditions).toEqual([]);
  });

  it('should leave the key requirement of a chain in place when an incomplete response follows it', async () => {
    const handler = createNoAvailableIndexersHandler();

    await handler.handle({ chain: 'optimism', reason: 'etherscan_paid_key_required' });
    await handler.handle({ chain: 'optimism', reason: 'blockscout_incomplete_response' });

    expect(useRaisedConditionsStore().conditions).toEqual([
      { cause: NoIndexersCause.PAID_ETHERSCAN_KEY, chain: 'optimism', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS },
    ]);
  });
});
