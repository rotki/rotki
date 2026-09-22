import { describe, expect, it } from 'vitest';
import { locationUsageEntries } from '@/modules/locations/location-usage';

describe('locationUsageEntries', () => {
  it('should list the uses most frequent first, keeping a kind it does not know by its name', () => {
    expect(locationUsageEntries({ children: 1, history_events: 12, new_table: 3 })).toEqual([
      { count: 12, kind: 'history_events', labelKey: 'location_manager.usage.kinds.history_events' },
      { count: 3, kind: 'new_table', labelKey: undefined },
      { count: 1, kind: 'children', labelKey: 'location_manager.usage.kinds.children' },
    ]);
  });
});
