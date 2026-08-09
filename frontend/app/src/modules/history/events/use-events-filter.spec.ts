import { assert, describe, expect, it } from 'vitest';
import { FilterBehaviours } from '@/modules/core/table/filtering';
import { transformFilters } from '@/modules/core/table/param-sources';
import { useHistoryEventFilter } from '@/modules/history/events/use-events-filter';

describe('useHistoryEventFilter', () => {
  it('should start with an empty filter', () => {
    const { filters } = useHistoryEventFilter();

    expect(get(filters)).toEqual({});
  });

  // The backend takes entry types as `{ behaviour, values }` so a type can be excluded. Nothing
  // covered that before: the flag lived on the matcher and no test read it, so losing it would have
  // sent a bare list and silently dropped the exclusion.
  describe('behaviour keys', () => {
    it('should declare entry types as behaviour-carrying', () => {
      const schema = useHistoryEventFilter();

      expect(schema.behaviourKeys).toStrictEqual(['entryTypes']);
    });

    it('should wrap an excluded entry type for the request', () => {
      const schema = useHistoryEventFilter();

      expect(transformFilters({ entryTypes: ['!evm event'] }, schema.behaviourKeys ?? []))
        .toStrictEqual({ entryTypes: { behaviour: FilterBehaviours.EXCLUDE, values: ['evm event'] } });
    });
  });

  describe('route filters', () => {
    it('should coerce single route values into arrays where the request takes many', () => {
      const { RouteFilterSchema } = useHistoryEventFilter();
      assert(RouteFilterSchema);

      expect(RouteFilterSchema.parse({ asset: 'ETH', entryTypes: 'evm event', txRefs: '0xabc' }))
        .toEqual({ asset: 'ETH', entryTypes: ['evm event'], txRefs: ['0xabc'] });
    });

    it('should keep the two period bounds as they are sent', () => {
      const { RouteFilterSchema } = useHistoryEventFilter();
      assert(RouteFilterSchema);

      expect(RouteFilterSchema.parse({ fromTimestamp: '1700000000', toTimestamp: '1700086400' }))
        .toEqual({ fromTimestamp: '1700000000', toTimestamp: '1700086400' });
    });

    it('should allow an empty route filter', () => {
      const { RouteFilterSchema } = useHistoryEventFilter();
      assert(RouteFilterSchema);

      expect(RouteFilterSchema.parse({})).toEqual({});
    });
  });
});
