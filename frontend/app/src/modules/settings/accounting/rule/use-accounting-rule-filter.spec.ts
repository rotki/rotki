import { describe, expect, it } from 'vitest';
import { useAccountingRuleFilter } from '@/modules/settings/accounting/rule/use-accounting-rule-filter';

describe('useAccountingRuleFilter', () => {
  it('should start with an empty filter', () => {
    const { filters } = useAccountingRuleFilter();

    expect(get(filters)).toEqual({});
  });

  // The URL round-trip is asserted in `accounting-rule-fields.spec.ts`, against the field list the
  // url shape is now derived from.
});
