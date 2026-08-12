import type { SnapshotListFilters } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { toSnapshotListMatches, useSnapshotListFields } from '@/modules/dashboard/snapshots/composables/use-snapshot-list-fields';

describe('useSnapshotListFields', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  it('should offer a single period field over the two list bounds', () => {
    const fields = useSnapshotListFields();
    expect(fields).toHaveLength(1);
    expect(fields[0]).toMatchObject({
      bounds: { lower: 'fromTimestamp', upper: 'toTimestamp' },
      key: 'period',
      valueType: 'date',
    });
  });
});

/**
 * The list filters on an object of unix seconds and mirrors it into the URL; the bar speaks the
 * flat keyword map. Everything here is about that bridge.
 */
describe('toSnapshotListMatches', () => {
  it('should pass the filter bounds to the bar as strings', () => {
    const filters = ref<SnapshotListFilters>({ fromTimestamp: 1600000000, toTimestamp: 1700000000 });
    expect(toSnapshotListMatches(filters).value).toEqual({
      fromTimestamp: '1600000000',
      toTimestamp: '1700000000',
    });
  });

  it('should send no bound the filters do not hold', () => {
    const filters = ref<SnapshotListFilters>({ fromTimestamp: 1600000000 });
    expect(toSnapshotListMatches(filters).value).toEqual({ fromTimestamp: '1600000000' });
  });

  it('should write the bounds the bar reports back as numbers', () => {
    const filters = ref<SnapshotListFilters>({});
    toSnapshotListMatches(filters).value = { fromTimestamp: '1600000000', toTimestamp: '1700000000' };
    expect(filters.value).toEqual({ fromTimestamp: 1600000000, toTimestamp: 1700000000 });
  });

  it('should clear a bound the bar dropped', () => {
    const filters = ref<SnapshotListFilters>({ fromTimestamp: 1600000000, toTimestamp: 1700000000 });
    toSnapshotListMatches(filters).value = { fromTimestamp: '1600000000' };
    expect(filters.value).toEqual({ fromTimestamp: 1600000000, toTimestamp: undefined });
  });
});
