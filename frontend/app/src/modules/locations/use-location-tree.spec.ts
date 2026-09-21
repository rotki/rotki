import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLocationTree } from '@/modules/locations/use-location-tree';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

const { fetchLocationTree } = vi.hoisted(() => ({
  fetchLocationTree: vi.fn(),
}));

vi.mock('@/modules/locations/use-location-tree-api', () => ({
  useLocationTreeApi: (): Record<string, unknown> => ({ fetchLocationTree }),
}));

describe('useLocationTree', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
  });

  it('should replace the stored tree with the one the backend returns', async () => {
    const store = useLocationTreeStore();
    store.setNodes([node('total', null, 'Total'), node('custom:old', 'total', 'Old', { isBuiltin: false })]);
    const fresh = [node('total', null, 'Total'), node('banks', 'total', 'Banks')];
    fetchLocationTree.mockResolvedValue(fresh);

    await useLocationTree().refreshLocationTree();

    expect(store.nodes).toEqual(fresh);
  });

  it('should keep the stored tree when the backend request fails', async () => {
    const store = useLocationTreeStore();
    const kept = [node('total', null, 'Total')];
    store.setNodes(kept);
    fetchLocationTree.mockRejectedValue(new Error('backend down'));

    await expect(useLocationTree().refreshLocationTree()).rejects.toThrow('backend down');
    expect(store.nodes).toEqual(kept);
  });
});
