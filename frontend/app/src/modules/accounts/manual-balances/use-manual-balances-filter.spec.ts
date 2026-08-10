import { describe, expect, it } from 'vitest';
import {
  ManualBalancesFilterSchema,
  useManualBalanceFilter,
} from '@/modules/accounts/manual-balances/use-manual-balances-filter';

describe('useManualBalanceFilter', () => {
  it('should start with an empty filter', () => {
    const { filters } = useManualBalanceFilter();

    expect(get(filters)).toEqual({});
  });

  // The URL round-trip is asserted in `manual-balance-fields.spec.ts`, against the field list the
  // url shape is now derived from.
});

describe('manualBalancesFilterSchema', () => {
  it('should split a comma-separated tags string into an array', () => {
    expect(ManualBalancesFilterSchema.parse({ tags: 'a,b,c' })).toEqual({ tags: ['a', 'b', 'c'] });
  });

  it('should default missing tags to an empty array', () => {
    expect(ManualBalancesFilterSchema.parse({})).toEqual({ tags: [] });
  });
});
