import { createLocationNode as node } from '@test/utils/location-tree';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLocationManagement } from '@/modules/locations/use-location-management';

const {
  addLocation,
  deleteLocation,
  deleteLocationImage,
  editLocation,
  fetchLocationUsage,
  refreshLocationTree,
  uploadLocationImage,
} = vi.hoisted(() => ({
  addLocation: vi.fn(),
  deleteLocation: vi.fn(),
  deleteLocationImage: vi.fn(),
  editLocation: vi.fn(),
  fetchLocationUsage: vi.fn(),
  refreshLocationTree: vi.fn(),
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

vi.mock('@/modules/locations/use-location-tree', () => ({
  useLocationTree: (): Record<string, unknown> => ({ refreshLocationTree }),
}));

describe('useLocationManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    refreshLocationTree.mockResolvedValue(undefined);
  });

  it('should reload the tree after a change is saved', async () => {
    const ing = node('custom:ing', 'banks', 'ING', { isBuiltin: false });
    addLocation.mockResolvedValue(ing);

    const outcome = await useLocationManagement().createLocation({ name: 'ING', parentIdentifier: 'banks' });

    assert(outcome.ok);
    expect(outcome.value).toEqual(ing);
    expect(refreshLocationTree).toHaveBeenCalledOnce();
  });

  it('should hand back the backend message of a refused change and keep the tree', async () => {
    editLocation.mockRejectedValue(new Error('A location named ING already exists at the same level'));

    const outcome = await useLocationManagement().editLocation('custom:dkb', { name: 'ING' });

    assert(!outcome.ok);
    expect(outcome.error).toBe('A location named ING already exists at the same level');
    expect(refreshLocationTree).not.toHaveBeenCalled();
  });

  it('should only check a previewed edit, and always save a real one', async () => {
    editLocation.mockResolvedValue({ location: node('custom:ing', 'other', 'ING'), newPath: [], oldPath: [] });
    const { editLocation: edit, previewEdit } = useLocationManagement();

    await previewEdit('custom:ing', { parentIdentifier: 'other' });
    expect(editLocation).toHaveBeenLastCalledWith('custom:ing', { dryRun: true, parentIdentifier: 'other' });
    expect(refreshLocationTree).not.toHaveBeenCalled();

    await edit('custom:ing', { dryRun: true, parentIdentifier: 'other' });
    expect(editLocation).toHaveBeenLastCalledWith('custom:ing', { dryRun: false, parentIdentifier: 'other' });
    expect(refreshLocationTree).toHaveBeenCalledOnce();
  });

  it('should read the usage of a location without reloading the tree', async () => {
    fetchLocationUsage.mockResolvedValue({ deletable: false, usage: { historyEvents: 2 } });

    const outcome = await useLocationManagement().fetchUsage('custom:ing');

    assert(outcome.ok);
    expect(outcome.value).toEqual({ deletable: false, usage: { historyEvents: 2 } });
    expect(fetchLocationUsage).toHaveBeenCalledWith('custom:ing');
    expect(refreshLocationTree).not.toHaveBeenCalled();
  });

  it('should hand back the message of a usage that could not be read', async () => {
    fetchLocationUsage.mockRejectedValue(new Error('Location custom:gone does not exist'));

    const outcome = await useLocationManagement().fetchUsage('custom:gone');

    assert(!outcome.ok);
    expect(outcome.error).toBe('Location custom:gone does not exist');
  });

  it('should reload the tree after a location is deleted', async () => {
    deleteLocation.mockResolvedValue(true);

    const outcome = await useLocationManagement().deleteLocation('custom:ing');

    assert(outcome.ok);
    expect(deleteLocation).toHaveBeenCalledWith('custom:ing');
    expect(refreshLocationTree).toHaveBeenCalledOnce();
  });

  it('should reload the tree after an image upload, handing back the stored image name', async () => {
    uploadLocationImage.mockResolvedValue('abc.png');
    const file = new File(['png'], 'logo.png');

    const outcome = await useLocationManagement().uploadImage('custom:ing', file);

    assert(outcome.ok);
    expect(outcome.value).toBe('abc.png');
    expect(uploadLocationImage).toHaveBeenCalledWith('custom:ing', file);
    expect(refreshLocationTree).toHaveBeenCalledOnce();
  });

  it('should reload the tree after an image is removed', async () => {
    deleteLocationImage.mockResolvedValue(true);

    const outcome = await useLocationManagement().removeImage('custom:ing');

    assert(outcome.ok);
    expect(deleteLocationImage).toHaveBeenCalledWith('custom:ing');
    expect(refreshLocationTree).toHaveBeenCalledOnce();
  });

  it('should reload the tree once after a batch of changes', async () => {
    addLocation.mockResolvedValue(node('custom:ing', 'banks', 'ING', { isBuiltin: false }));
    uploadLocationImage.mockResolvedValue('abc.png');
    const { batch, createLocation, uploadImage } = useLocationManagement();

    await batch(async () => {
      await createLocation({ name: 'ING', parentIdentifier: 'banks' });
      await uploadImage('custom:ing', new File(['png'], 'logo.png'));
      expect(refreshLocationTree).not.toHaveBeenCalled();
    });

    expect(refreshLocationTree).toHaveBeenCalledOnce();
    await useLocationManagement().removeImage('custom:ing');
    expect(refreshLocationTree).toHaveBeenCalledTimes(2);
  });

  it('should share one reload between nested batches, after the outer one ends', async () => {
    addLocation.mockResolvedValue(node('custom:ing', 'banks', 'ING', { isBuiltin: false }));
    uploadLocationImage.mockResolvedValue('abc.png');
    const { batch, createLocation, uploadImage } = useLocationManagement();

    const created = await batch(async () => {
      await createLocation({ name: 'ING', parentIdentifier: 'banks' });
      await batch(async () => uploadImage('custom:ing', new File(['png'], 'logo.png')));
      expect(refreshLocationTree).not.toHaveBeenCalled();
      return 'done';
    });

    expect(created).toBe('done');
    expect(refreshLocationTree).toHaveBeenCalledOnce();
  });

  it('should not reload the tree after a batch where nothing was saved', async () => {
    addLocation.mockRejectedValue(new Error('A location named ING already exists at the same level'));
    const { batch, createLocation } = useLocationManagement();

    await batch(async () => {
      await createLocation({ name: 'ING', parentIdentifier: 'banks' });
    });

    expect(refreshLocationTree).not.toHaveBeenCalled();
  });

  it('should keep the tree when a delete is refused', async () => {
    deleteLocation.mockRejectedValue(new Error('Location custom:ing is still in use'));

    const outcome = await useLocationManagement().deleteLocation('custom:ing');

    assert(!outcome.ok);
    expect(outcome.error).toBe('Location custom:ing is still in use');
    expect(refreshLocationTree).not.toHaveBeenCalled();
  });
});
