import { describe, expect, it } from 'vitest';
import { ManualBalancesFilterSchema } from '@/modules/accounts/manual-balances/use-manual-balances-filter';

describe('manualBalancesFilterSchema', () => {
  it('should split a comma-separated tags string into an array', () => {
    expect(ManualBalancesFilterSchema.parse({ tags: 'a,b,c' })).toEqual({ tags: ['a', 'b', 'c'] });
  });

  it('should default missing tags to an empty array', () => {
    expect(ManualBalancesFilterSchema.parse({})).toEqual({ tags: [] });
  });
});
