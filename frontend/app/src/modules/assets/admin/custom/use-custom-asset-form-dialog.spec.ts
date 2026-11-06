import type { CustomAsset } from '@/modules/assets/types';
import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref, shallowRef } from 'vue';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { useCustomAssetFormDialog } from './use-custom-asset-form-dialog';

const { addCustomAsset, editCustomAsset, saveIcon, validate } = vi.hoisted(() => ({
  addCustomAsset: vi.fn(),
  editCustomAsset: vi.fn(),
  saveIcon: vi.fn(),
  validate: vi.fn(() => true),
}));

vi.mock('@/modules/assets/api/use-asset-management-api', () => ({
  useAssetManagementApi: (): Record<string, unknown> => ({ addCustomAsset, editCustomAsset }),
}));

const BLANK: CustomAsset = { customAssetType: '', identifier: '', name: '', notes: '' };

function asset(overrides: Partial<CustomAsset> = {}): CustomAsset {
  return { customAssetType: 'real estate', identifier: 'custom-1', name: 'A house', notes: '', ...overrides };
}

let open: Ref<boolean>;
let editableItem: Ref<CustomAsset | null>;
let form: Ref<{ saveIcon: typeof saveIcon; validate: typeof validate } | null>;
let onSaved: ReturnType<typeof vi.fn<(identifier: string) => void>>;
let scope: ReturnType<typeof effectScope>;

function dialog(): ReturnType<typeof useCustomAssetFormDialog> {
  scope = effectScope();
  return scope.run(() => useCustomAssetFormDialog({ editableItem, form, onSaved, open }))!;
}

describe('modules/assets/admin/custom/useCustomAssetFormDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    open = ref<boolean>(true);
    editableItem = ref<CustomAsset | null>(null);
    form = shallowRef({ saveIcon, validate });
    onSaved = vi.fn<(identifier: string) => void>();
    validate.mockReturnValue(true);
    addCustomAsset.mockResolvedValue('custom-new');
    editCustomAsset.mockResolvedValue(true);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('what the form binds', () => {
    it('should offer a blank asset when adding', () => {
      const { modelValue } = dialog();

      expect(get(modelValue)).toEqual(BLANK);
    });

    it('should offer the asset being edited', () => {
      set(editableItem, asset());

      const { modelValue } = dialog();

      expect(get(modelValue)).toEqual(asset());
    });

    it('should hold nothing while the dialog is closed', () => {
      set(open, false);

      const { modelValue } = dialog();

      expect(get(modelValue)).toBeUndefined();
    });

    it('should follow the dialog closing', async () => {
      const { modelValue } = dialog();
      set(open, false);
      await flushPromises();

      expect(get(modelValue)).toBeUndefined();
    });

    it('should follow a change of asset while open', async () => {
      const { modelValue } = dialog();
      set(editableItem, asset({ name: 'A boat' }));
      await flushPromises();

      expect(get(modelValue)).toEqual(asset({ name: 'A boat' }));
    });
  });

  describe('the title', () => {
    it('should say add while creating', () => {
      const { dialogTitle } = dialog();

      expect(get(dialogTitle)).toBe('asset_management.add_title');
    });

    it('should say edit while editing', () => {
      set(editableItem, asset());

      const { dialogTitle } = dialog();

      expect(get(dialogTitle)).toBe('asset_management.edit_title');
    });
  });

  describe('before it writes anything', () => {
    it('should write nothing while the dialog is closed', async () => {
      set(open, false);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(addCustomAsset).not.toHaveBeenCalled();
    });

    it('should write nothing while the form is invalid', async () => {
      validate.mockReturnValue(false);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(addCustomAsset).not.toHaveBeenCalled();
    });

    it('should write nothing when the form is not mounted', async () => {
      set(form, null);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(addCustomAsset).not.toHaveBeenCalled();
    });
  });

  describe('adding an asset', () => {
    it('should send it without the identifier the backend assigns', async () => {
      const { modelValue, save } = dialog();
      set(modelValue, asset({ identifier: 'ignored' }));
      await save();

      expect(addCustomAsset).toHaveBeenCalledWith({
        customAssetType: 'real estate',
        name: 'A house',
        notes: '',
      });
      expect(editCustomAsset).not.toHaveBeenCalled();
    });

    it('should hand the caller the identifier the backend assigned', async () => {
      const { save } = dialog();

      expect(await save()).toBe(true);
      expect(onSaved).toHaveBeenCalledWith('custom-new');
      expect(saveIcon).toHaveBeenCalledWith('custom-new');
    });

    it('should fail when the backend assigns no identifier', async () => {
      addCustomAsset.mockResolvedValue('');

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(onSaved).not.toHaveBeenCalled();
      expect(saveIcon).not.toHaveBeenCalled();
    });
  });

  describe('editing an asset', () => {
    beforeEach(() => {
      set(editableItem, asset());
    });

    it('should send the asset as it stands', async () => {
      const { save } = dialog();
      await save();

      expect(editCustomAsset).toHaveBeenCalledWith(asset());
      expect(addCustomAsset).not.toHaveBeenCalled();
    });

    it('should keep the identifier it already had', async () => {
      const { save } = dialog();

      expect(await save()).toBe(true);
      expect(onSaved).toHaveBeenCalledWith('custom-1');
      expect(saveIcon).toHaveBeenCalledWith('custom-1');
    });

    it('should keep the dialog open when the backend refuses', async () => {
      editCustomAsset.mockResolvedValue(false);

      const { modelValue, save } = dialog();

      expect(await save()).toBe(false);
      expect(onSaved).not.toHaveBeenCalled();
      expect(get(modelValue)).toBeDefined();
    });
  });

  describe('when the write throws', () => {
    it('should keep an add failure for the dialog, titled with the adding wording', async () => {
      const error = new Error('the backend is down');
      addCustomAsset.mockRejectedValue(error);

      const { failure, failureTitle, save } = dialog();

      expect(await save()).toBe(false);
      expect(get(failure)).toBe(error);
      expect(get(failureTitle)).toBe('asset_management.add_error');
    });

    it('should title an edit failure with the editing wording', async () => {
      set(editableItem, asset());
      editCustomAsset.mockRejectedValue(new Error('the backend is down'));

      const { failureTitle, save } = dialog();
      await save();

      expect(get(failureTitle)).toBe('asset_management.edit_error');
    });

    it('should put a validation error on a field of the asset onto that field', async () => {
      addCustomAsset.mockRejectedValue(new ApiValidationError(JSON.stringify({ name: ['already taken'] })));

      const { failure, modelErrorMessages, save } = dialog();
      await save();

      expect(get(modelErrorMessages)).toEqual({ name: ['already taken'] });
      expect(get(failure)).toBeUndefined();
    });

    it('should stop loading so the user can try again', async () => {
      addCustomAsset.mockRejectedValue(new Error('boom'));

      const { loading, save } = dialog();
      await save();

      expect(get(loading)).toBe(false);
    });
  });

  it('should mark itself loading only while the write runs', async () => {
    const { loading, save } = dialog();

    const pending = save();
    expect(get(loading)).toBe(true);

    await pending;
    expect(get(loading)).toBe(false);
  });
});
