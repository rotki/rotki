import { createLocationNode as node } from '@test/utils/location-tree';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLocationManagement } from '@/modules/locations/use-location-management';

const { addLocation, editLocation, refreshLocationTree } = vi.hoisted(() => ({
  addLocation: vi.fn(),
  editLocation: vi.fn(),
  refreshLocationTree: vi.fn(),
}));

vi.mock('@/modules/locations/use-location-tree-api', () => ({
  useLocationTreeApi: (): Record<string, unknown> => ({ addLocation, editLocation }),
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
});
