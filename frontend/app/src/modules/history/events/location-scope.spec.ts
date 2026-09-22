import { describe, expect, it } from 'vitest';
import { withLocationScope } from '@/modules/history/events/location-scope';

describe('withLocationScope', () => {
  it('should widen a location filter to the locations below it', () => {
    expect(withLocationScope({ limit: 10, location: 'banks' })).toEqual({ limit: 10, location: 'banks', locationScope: 'subtree' });
  });

  it('should keep an explicit scope and leave requests without a location alone', () => {
    expect(withLocationScope({ location: 'banks', locationScope: 'exact' as const })).toEqual({ location: 'banks', locationScope: 'exact' });
    const unfiltered: { limit: number; location?: string } = { limit: 10 };
    expect(withLocationScope(unfiltered)).toEqual({ limit: 10 });
  });
});
