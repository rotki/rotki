import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { setActivePinia } from 'pinia';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLocationManagement } from '@/modules/locations/use-location-management';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

const {
  addLocation,
  deleteLocation,
  deleteLocationImage,
  editLocation,
  fetchLocationUsage,
  uploadLocationImage,
} = vi.hoisted(() => ({
  addLocation: vi.fn(),
  deleteLocation: vi.fn(),
  deleteLocationImage: vi.fn(),
  editLocation: vi.fn(),
  fetchLocationUsage: vi.fn(),
  uploadLocationImage: vi.fn(),
}));

vi.mock('@/modules/locations/use-location-tree-api', () => ({
  useLocationTreeApi: (): Record<string, unknown> => ({
    addLocation,
    deleteLocation,
    deleteLocationImage,
    editLocation,
    fetchLocationUsage,
    uploadLocationImage,
  }),
}));

const ing = node('custom:ing', 'banks', 'ING', { isBuiltin: false });

function identifiers(): string[] {
  return useLocationTreeStore().nodes.map(item => item.identifier);
}

describe('useLocationManagement', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    useLocationTreeStore().setNodes([node('total', null, 'Total'), node('banks', 'total', 'Banks'), ing]);
  });

  it('should add a created location to the tree', async () => {
    const dkb = node('custom:dkb', 'banks', 'DKB', { isBuiltin: false });
    addLocation.mockResolvedValue(dkb);

    const outcome = await useLocationManagement().createLocation({ name: 'DKB', parentIdentifier: 'banks' });

    assert(outcome.ok);
    expect(outcome.value).toEqual(dkb);
    expect(useLocationTreeStore().getNode('custom:dkb')).toEqual(dkb);
  });

  it('should replace an edited location with the one the backend returns', async () => {
    const moved = { ...ing, name: 'ING DiBa', parentIdentifier: 'total' };
    editLocation.mockResolvedValue({ location: moved, newPath: ['Total', 'ING DiBa'], oldPath: ['Total', 'Banks', 'ING'] });

    const outcome = await useLocationManagement().editLocation('custom:ing', { name: 'ING DiBa', parentIdentifier: 'total' });

    assert(outcome.ok);
    expect(useLocationTreeStore().getNode('custom:ing')).toEqual(moved);
    expect(identifiers()).toEqual(['total', 'banks', 'custom:ing']);
  });

  it('should hand back the backend message of a refused change and keep the tree', async () => {
    editLocation.mockRejectedValue(new Error('A location named ING already exists at the same level'));

    const outcome = await useLocationManagement().editLocation('custom:ing', { name: 'ING' });

    assert(!outcome.ok);
    expect(outcome.error).toBe('A location named ING already exists at the same level');
    expect(useLocationTreeStore().getNode('custom:ing')).toEqual(ing);
  });

  it('should only check a previewed edit, and always save a real one', async () => {
    editLocation.mockResolvedValue({ location: { ...ing, parentIdentifier: 'total' }, newPath: [], oldPath: [] });
    const { editLocation: save, previewEdit } = useLocationManagement();

    await previewEdit('custom:ing', { dryRun: false, parentIdentifier: 'total' });
    expect(editLocation).toHaveBeenLastCalledWith('custom:ing', { dryRun: true, parentIdentifier: 'total' });
    expect(useLocationTreeStore().getNode('custom:ing')).toEqual(ing);

    await save('custom:ing', { dryRun: true, parentIdentifier: 'total' });
    expect(editLocation).toHaveBeenLastCalledWith('custom:ing', { dryRun: false, parentIdentifier: 'total' });
  });

  it('should read the usage of a location without changing the tree', async () => {
    fetchLocationUsage.mockResolvedValue({ deletable: false, usage: { historyEvents: 2 } });

    const outcome = await useLocationManagement().fetchUsage('custom:ing');

    assert(outcome.ok);
    expect(outcome.value).toEqual({ deletable: false, usage: { historyEvents: 2 } });
    expect(identifiers()).toEqual(['total', 'banks', 'custom:ing']);
  });

  it('should hand back the message of a usage that could not be read', async () => {
    fetchLocationUsage.mockRejectedValue(new Error('Location custom:ing does not exist'));

    const outcome = await useLocationManagement().fetchUsage('custom:ing');

    assert(!outcome.ok);
    expect(outcome.error).toBe('Location custom:ing does not exist');
  });

  it('should remove a deleted location from the tree', async () => {
    deleteLocation.mockResolvedValue(true);

    const outcome = await useLocationManagement().deleteLocation('custom:ing');

    assert(outcome.ok);
    expect(identifiers()).toEqual(['total', 'banks']);
  });

  it('should keep a location whose delete is refused', async () => {
    deleteLocation.mockRejectedValue(new Error('Location custom:ing is in use'));

    const outcome = await useLocationManagement().deleteLocation('custom:ing');

    assert(!outcome.ok);
    expect(identifiers()).toEqual(['total', 'banks', 'custom:ing']);
  });

  it('should store the image name of an upload on its location', async () => {
    uploadLocationImage.mockResolvedValue('custom%3Aing_ab12.png');

    const outcome = await useLocationManagement().uploadImage('custom:ing', new File(['png'], 'logo.png'));

    assert(outcome.ok);
    expect(outcome.value).toBe('custom%3Aing_ab12.png');
    expect(useLocationTreeStore().getNode('custom:ing')?.image).toBe('custom%3Aing_ab12.png');
  });

  it('should clear the image of a location once it is removed', async () => {
    useLocationTreeStore().upsertNode({ ...ing, image: 'custom%3Aing_ab12.png' });
    deleteLocationImage.mockResolvedValue(true);

    const outcome = await useLocationManagement().removeImage('custom:ing');

    assert(outcome.ok);
    expect(useLocationTreeStore().getNode('custom:ing')?.image).toBeNull();
  });
});
