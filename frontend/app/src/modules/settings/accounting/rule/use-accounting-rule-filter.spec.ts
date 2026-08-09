import { assert, describe, expect, it } from 'vitest';
import { useAccountingRuleFilter } from '@/modules/settings/accounting/rule/use-accounting-rule-filter';

describe('useAccountingRuleFilter', () => {
  it('should start with an empty filter', () => {
    const { filters } = useAccountingRuleFilter();

    expect(get(filters)).toEqual({});
  });

  it('should coerce single route values into arrays', () => {
    const { RouteFilterSchema } = useAccountingRuleFilter();
    assert(RouteFilterSchema);

    expect(RouteFilterSchema.parse({ counterparties: 'uniswap', eventTypes: 'spend' }))
      .toEqual({ counterparties: ['uniswap'], eventTypes: ['spend'] });
  });

  it('should allow an empty route filter', () => {
    const { RouteFilterSchema } = useAccountingRuleFilter();
    assert(RouteFilterSchema);

    expect(RouteFilterSchema.parse({})).toEqual({});
  });
});
