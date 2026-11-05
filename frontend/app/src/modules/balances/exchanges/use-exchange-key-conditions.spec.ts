import { beforeEach, describe, expect, it } from 'vitest';
import { useExchangeKeyConditions } from '@/modules/balances/exchanges/use-exchange-key-conditions';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

const main = { location: 'binance', name: 'main' };
const other = { location: 'kraken', name: 'main' };

describe('useExchangeKeyConditions', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    const { raise } = useRaisedConditionsStore();
    raise({ kind: RaisedConditionKind.EXCHANGE_KEY_REJECTED, ...main });
    raise({ kind: RaisedConditionKind.EXCHANGE_KEY_REJECTED, ...other });
    raise({ identifier: 'binance-main', kind: RaisedConditionKind.BINANCE_PAIRS_MISSING, ...main });
  });

  it('should list the accounts whose key was refused, and no other condition', () => {
    const { accounts } = useExchangeKeyConditions();

    expect(get(accounts)).toEqual([main, other]);
  });

  it('should settle only the account that was saved', () => {
    const { accounts, settleSaved } = useExchangeKeyConditions();

    settleSaved(main);

    expect(get(accounts)).toEqual([other]);
    expect(useRaisedConditionsStore().conditions).toContainEqual({ identifier: 'binance-main', kind: RaisedConditionKind.BINANCE_PAIRS_MISSING, ...main });
  });

  it('should settle the accounts that are no longer connected', () => {
    const { accounts, settleDisconnected } = useExchangeKeyConditions();

    settleDisconnected([other]);

    expect(get(accounts)).toEqual([other]);
    expect(useRaisedConditionsStore().conditions).toContainEqual({ identifier: 'binance-main', kind: RaisedConditionKind.BINANCE_PAIRS_MISSING, ...main });
  });
});
