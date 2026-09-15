import { beforeEach, describe, expect, it } from 'vitest';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

describe('modules/shell/action-center/use-raised-conditions-store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should keep one entry per subject, holding the latest report', () => {
    const store = useRaisedConditionsStore();

    store.raise({ chain: 'gnosis', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS, paidKeyRequired: false });
    store.raise({ chain: 'gnosis', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS, paidKeyRequired: true });

    expect(store.conditions).toEqual([{ chain: 'gnosis', kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS, paidKeyRequired: true }]);
  });

  it('should keep separate entries for different subjects of the same kind', () => {
    const store = useRaisedConditionsStore();

    store.raise({ kind: RaisedConditionKind.MISSING_API_KEY, service: 'etherscan' });
    store.raise({ kind: RaisedConditionKind.MISSING_API_KEY, service: 'helius' });

    expect(store.conditions).toHaveLength(2);
  });

  it('should clear only the conditions the predicate matches', () => {
    const store = useRaisedConditionsStore();

    store.raise({ kind: RaisedConditionKind.MISSING_API_KEY, service: 'etherscan' });
    store.raise({ kind: RaisedConditionKind.MONERIUM_SESSION });

    store.clear(condition => condition.kind === RaisedConditionKind.MISSING_API_KEY && condition.service === 'etherscan');

    expect(store.conditions).toEqual([{ kind: RaisedConditionKind.MONERIUM_SESSION }]);
  });

  it('should leave the record untouched when nothing matches', () => {
    const store = useRaisedConditionsStore();
    store.raise({ kind: RaisedConditionKind.GNOSIS_PAY_SESSION });
    const before = store.raised;

    store.clear(condition => condition.kind === RaisedConditionKind.MONERIUM_SESSION);

    expect(store.raised).toBe(before);
  });
});
