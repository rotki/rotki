import { assert, describe, expect, it } from 'vitest';
import {
  ManualBalancesFilterSchema,
  useManualBalanceFilter,
} from '@/modules/accounts/manual-balances/use-manual-balances-filter';

describe('useManualBalanceFilter', () => {
  it('should start with an empty filter', () => {
    const { filters } = useManualBalanceFilter();

    expect(get(filters)).toEqual({});
  });

  it('should parse optional route filter values', () => {
    const { RouteFilterSchema } = useManualBalanceFilter();
    assert(RouteFilterSchema);

    expect(RouteFilterSchema.parse({ asset: 'ETH', label: 'x', location: 'kraken' })).toEqual({
      asset: 'ETH',
      label: 'x',
      location: 'kraken',
    });
    expect(RouteFilterSchema.parse({})).toEqual({});
  });
});

describe('manualBalancesFilterSchema', () => {
  it('should split a comma-separated tags string into an array', () => {
    expect(ManualBalancesFilterSchema.parse({ tags: 'a,b,c' })).toEqual({ tags: ['a', 'b', 'c'] });
  });

  it('should default missing tags to an empty array', () => {
    expect(ManualBalancesFilterSchema.parse({})).toEqual({ tags: [] });
  });
});
