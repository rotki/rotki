import { beforeEach, describe, expect, it } from 'vitest';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';
import { createBinancePairsMissingHandler } from './binance-pairs-missing';

describe('modules/core/messaging/handlers/binance-pairs-missing', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should list the account in the action center, with no notification', async () => {
    const result = await createBinancePairsMissingHandler().handle({ location: 'binance', name: 'main' });

    expect(result).toBeUndefined();
    expect(useRaisedConditionsStore().conditions).toEqual([{ kind: RaisedConditionKind.BINANCE_PAIRS_MISSING, location: 'binance', name: 'main' }]);
  });

  it('should keep one entry per account however often the history query repeats the report', async () => {
    const handler = createBinancePairsMissingHandler();
    await handler.handle({ location: 'binance', name: 'main' });
    await handler.handle({ location: 'binance', name: 'main' });
    await handler.handle({ location: 'binanceus', name: 'main' });

    expect(useRaisedConditionsStore().conditions).toHaveLength(2);
  });
});
