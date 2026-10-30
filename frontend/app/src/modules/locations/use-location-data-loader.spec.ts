import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useLocationDataLoader } from '@/modules/locations/use-location-data-loader';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

const { fetchAllLocations } = vi.hoisted(() => ({
  fetchAllLocations: vi.fn<() => Promise<{ locations: Record<string, { label?: string }> }>>(),
}));

vi.mock('@/modules/history/api/use-history-api', () => ({
  useHistoryApi: (): Record<string, unknown> => ({ fetchAllLocations }),
}));

describe('useLocationDataLoader', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    fetchAllLocations.mockResolvedValue({ locations: { kraken: { label: 'Kraken' } } });
  });

  it('should fill the location details and a tree of them', async () => {
    useLocationDataLoader().loadLocations();
    await flushPromises();

    expect(useLocationStore().allLocations).toEqual({ kraken: { label: 'Kraken' } });
    expect(useLocationTreeStore().nodes.map(node => node.identifier)).toEqual(['total', 'kraken']);
  });
});
