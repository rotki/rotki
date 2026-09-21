import { describe, expect, it } from 'vitest';
import { locationUsageEntries } from '@/modules/locations/location-usage';

describe('locationUsageEntries', () => {
  it('should label the camel-cased kinds the API client hands over, most frequent first', () => {
    expect(locationUsageEntries({ children: 1, historyEvents: 12, newTable: 3 }, 'custom:ing')).toEqual([
      {
        count: 12,
        kind: 'historyEvents',
        labelKey: 'location_manager.usage.kinds.history_events',
        to: { name: '/history/events/', query: { location: 'custom:ing' } },
      },
      { count: 3, kind: 'newTable', labelKey: undefined, to: undefined },
      { count: 1, kind: 'children', labelKey: 'location_manager.usage.kinds.children', to: undefined },
    ]);
  });

  it('should link manual balances and snapshot entries to their pages', () => {
    const entries = locationUsageEntries({ manuallyTrackedBalances: 1, timedLocationData: 2 }, 'custom:ing');
    expect(entries.map(entry => [entry.labelKey, entry.to])).toEqual([
      ['location_manager.usage.kinds.timed_location_data', { name: '/statistics/snapshots/' }],
      ['location_manager.usage.kinds.manually_tracked_balances', { name: '/balances/manual/[[tab]]' }],
    ]);
  });
});
