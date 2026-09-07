import type { SupportedAsset } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref, shallowRef } from 'vue';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { useManagedAssetFormDialog } from './use-managed-asset-form-dialog';

const { deleteCacheKey, saveAsset, saveIcon, setMessage, validate } = vi.hoisted(() => ({
  deleteCacheKey: vi.fn(),
  saveAsset: vi.fn(),
  saveIcon: vi.fn(),
  setMessage: vi.fn(),
  validate: vi.fn(() => true),
}));

vi.mock('@/modules/assets/use-asset-info-cache', () => ({
  useAssetInfoCache: (): Record<string, unknown> => ({ deleteCacheKey }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

const ASSET = createMock<SupportedAsset>({ identifier: 'eip155:1/erc20:0xABC', name: 'Token' });

let modelValue: Ref<SupportedAsset | undefined>;
let editMode: Ref<boolean>;
let form: Ref<{ saveAsset: typeof saveAsset; saveIcon: typeof saveIcon; validate: typeof validate } | null>;
let onSaved: ReturnType<typeof vi.fn<() => void>>;
let scope: ReturnType<typeof effectScope>;

function dialog(): ReturnType<typeof useManagedAssetFormDialog> {
  scope = effectScope();
  return scope.run(() => useManagedAssetFormDialog({
    editMode,
    form,
    modelValue,
    onSaved,
  }))!;
}

describe('modules/assets/admin/managed/useManagedAssetFormDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    modelValue = ref<SupportedAsset | undefined>(ASSET);
    editMode = shallowRef<boolean>(false);
    onSaved = vi.fn<() => void>();
    validate.mockReturnValue(true);
    saveAsset.mockResolvedValue('eip155:1/erc20:0xABC');
    form = shallowRef({ saveAsset, saveIcon, validate });
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the title', () => {
    it('should say add while creating', () => {
      const { dialogTitle } = dialog();

      expect(get(dialogTitle)).toBe('asset_management.add_title');
    });

    it('should say edit while editing', () => {
      set(editMode, true);

      const { dialogTitle } = dialog();

      expect(get(dialogTitle)).toBe('asset_management.edit_title');
    });
  });

  describe('before it writes anything', () => {
    it('should write nothing without an asset', async () => {
      set(modelValue, undefined);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(saveAsset).not.toHaveBeenCalled();
    });

    it('should write nothing while the form is invalid', async () => {
      validate.mockReturnValue(false);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(saveAsset).not.toHaveBeenCalled();
    });

    it('should write nothing when the form is not mounted', async () => {
      set(form, null);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(saveAsset).not.toHaveBeenCalled();
    });
  });

  describe('a write that lands', () => {
    it('should drop the stale cache entry and upload the icon', async () => {
      const { save } = dialog();

      expect(await save()).toBe(true);
      expect(deleteCacheKey).toHaveBeenCalledWith('eip155:1/erc20:0xABC');
      expect(saveIcon).toHaveBeenCalledWith('eip155:1/erc20:0xABC');
    });

    it('should close the dialog and ask the caller to refresh', async () => {
      const { save } = dialog();
      await save();

      expect(get(modelValue)).toBeUndefined();
      expect(onSaved).toHaveBeenCalledOnce();
    });

    it('should mark itself loading only while the write runs', async () => {
      const { loading, save } = dialog();

      const pending = save();
      expect(get(loading)).toBe(true);

      await pending;
      expect(get(loading)).toBe(false);
    });
  });

  describe('a write the form refuses', () => {
    it('should keep the dialog open when no identifier comes back', async () => {
      saveAsset.mockResolvedValue(undefined);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(deleteCacheKey).not.toHaveBeenCalled();
      expect(saveIcon).not.toHaveBeenCalled();
      expect(onSaved).not.toHaveBeenCalled();
      expect(get(modelValue)).toBeDefined();
    });

    it('should stop loading so the user can try again', async () => {
      saveAsset.mockRejectedValue(new Error('boom'));

      const { loading, save } = dialog();
      await save();

      expect(get(loading)).toBe(false);
    });
  });

  describe('reporting a failure', () => {
    it('should report a plain failure with the adding wording', async () => {
      saveAsset.mockRejectedValue(new Error('the backend is down'));

      const { save } = dialog();
      await save();

      expect(setMessage).toHaveBeenCalledWith({
        description: 'the backend is down',
        title: 'asset_form.add_error',
      });
    });

    it('should report a plain failure with the editing wording', async () => {
      set(editMode, true);
      saveAsset.mockRejectedValue(new Error('the backend is down'));

      const { save } = dialog();
      await save();

      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ title: 'asset_form.edit_error' }));
    });

    it('should put field errors on the form and re-validate so they surface', async () => {
      saveAsset.mockRejectedValue(new ApiValidationError(JSON.stringify({ name: ['is required'] })));

      const { modelErrorMessages, save } = dialog();
      validate.mockClear();
      await save();

      expect(get(modelErrorMessages)).toEqual({ name: ['is required'] });
      expect(validate).toHaveBeenCalledTimes(2);
      expect(setMessage).not.toHaveBeenCalled();
    });
  });

  describe('a failure with no single field to blame', () => {
    it('should report underlying tokens as a message, not on a field', async () => {
      saveAsset.mockRejectedValue(
        new ApiValidationError(JSON.stringify({ underlyingTokens: ['weights must add up to 100'] })),
      );

      const { modelErrorMessages, save } = dialog();
      await save();

      expect(setMessage).toHaveBeenCalledWith({
        description: 'weights must add up to 100',
        title: 'asset_form.underlying_tokens',
      });
      expect(get(modelErrorMessages)).toEqual({});
    });

    it('should join several underlying-token failures into one message', async () => {
      saveAsset.mockRejectedValue(
        new ApiValidationError(JSON.stringify({ underlyingTokens: ['too many', 'bad weight'] })),
      );

      const { save } = dialog();
      await save();

      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ description: 'too many,bad weight' }));
    });

    it('should report a whole-payload failure, which arrives camelCased as Schema', async () => {
      saveAsset.mockRejectedValue(new ApiValidationError(JSON.stringify({ _schema: ['the payload is wrong'] })));

      const { modelErrorMessages, save } = dialog();
      await save();

      expect(setMessage).toHaveBeenCalledWith({
        description: 'the payload is wrong',
        title: 'asset_form.underlying_tokens',
      });
      expect(get(modelErrorMessages)).toEqual({});
    });

    it('should report a single underlying-token failure that is not a list', async () => {
      saveAsset.mockRejectedValue(
        new ApiValidationError(JSON.stringify({ underlyingTokens: 'weights must add up to 100' })),
      );

      const { save } = dialog();
      await save();

      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({
        description: 'weights must add up to 100',
      }));
    });

    it('should report nothing when the payload failure is not a list', async () => {
      saveAsset.mockRejectedValue(new ApiValidationError(JSON.stringify({ _schema: 'the payload is wrong' })));

      const { save } = dialog();
      await save();

      expect(setMessage).not.toHaveBeenCalled();
    });

    it('should keep the field errors while reporting the payload one', async () => {
      saveAsset.mockRejectedValue(
        new ApiValidationError(JSON.stringify({ name: ['is required'], _schema: ['the payload is wrong'] })),
      );

      const { modelErrorMessages, save } = dialog();
      await save();

      expect(setMessage).toHaveBeenCalledOnce();
      expect(get(modelErrorMessages)).toEqual({ name: ['is required'] });
    });
  });
});
