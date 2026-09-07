import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref, shallowRef } from 'vue';
import { useMappingFormDialog } from './use-mapping-form-dialog';

const { add, edit, setMessage, validate } = vi.hoisted(() => ({
  add: vi.fn(async () => Promise.resolve(true)),
  edit: vi.fn(async () => Promise.resolve(true)),
  setMessage: vi.fn(),
  validate: vi.fn(() => true),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

interface Mapping {
  asset: string;
  location: string | null;
  locationSymbol: string;
}

const MAPPING: Mapping = { asset: 'BTC', location: 'kraken', locationSymbol: 'XBT' };

let modelValue: Ref<Mapping | undefined>;
let editMode: Ref<boolean>;
let form: Ref<{ validate: typeof validate } | null>;
let onSaved: ReturnType<typeof vi.fn<(mapping: Mapping) => void>>;
let toPayload: ReturnType<typeof vi.fn<(mapping: Mapping) => Mapping>>;
let scope: ReturnType<typeof effectScope>;

function dialog(): ReturnType<typeof useMappingFormDialog<Mapping, Mapping>> {
  scope = effectScope();
  return scope.run(() => useMappingFormDialog<Mapping, Mapping>({
    add,
    edit,
    editMode,
    form,
    modelValue,
    onSaved,
    toPayload,
  }))!;
}

describe('modules/assets/admin/useMappingFormDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    modelValue = ref<Mapping | undefined>({ ...MAPPING });
    editMode = shallowRef<boolean>(false);
    form = shallowRef({ validate });
    onSaved = vi.fn<(mapping: Mapping) => void>();
    toPayload = vi.fn<(mapping: Mapping) => Mapping>(mapping => mapping);
    validate.mockReturnValue(true);
    add.mockResolvedValue(true);
    edit.mockResolvedValue(true);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the title', () => {
    it('should say add while creating', () => {
      const { dialogTitle } = dialog();

      expect(get(dialogTitle)).toBe('asset_management.cex_mapping.add_title');
    });

    it('should say edit while editing', () => {
      set(editMode, true);

      const { dialogTitle } = dialog();

      expect(get(dialogTitle)).toBe('asset_management.cex_mapping.edit_title');
    });
  });

  describe('before it writes anything', () => {
    it('should write nothing without a mapping', async () => {
      set(modelValue, undefined);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(add).not.toHaveBeenCalled();
      expect(edit).not.toHaveBeenCalled();
    });

    it('should write nothing while the form is invalid', async () => {
      validate.mockReturnValue(false);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(add).not.toHaveBeenCalled();
    });

    it('should write nothing when the form is not mounted', async () => {
      set(form, null);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(add).not.toHaveBeenCalled();
    });
  });

  describe('writing', () => {
    it('should add a new mapping', async () => {
      const { save } = dialog();

      expect(await save()).toBe(true);
      expect(add).toHaveBeenCalledWith(MAPPING);
      expect(edit).not.toHaveBeenCalled();
    });

    it('should edit an existing mapping', async () => {
      set(editMode, true);

      const { save } = dialog();
      await save();

      expect(edit).toHaveBeenCalledWith(MAPPING);
      expect(add).not.toHaveBeenCalled();
    });

    it('should send what the caller turns the mapping into', async () => {
      toPayload.mockImplementation(mapping => ({ ...mapping, location: null }));

      const { save } = dialog();
      await save();

      expect(add).toHaveBeenCalledWith({ asset: 'BTC', location: null, locationSymbol: 'XBT' });
    });

    it('should close the dialog and hand the mapping back once it lands', async () => {
      const { save } = dialog();
      await save();

      expect(get(modelValue)).toBeUndefined();
      expect(onSaved).toHaveBeenCalledWith(MAPPING);
    });

    it('should hand back the mapping as edited, not the payload it sent', async () => {
      toPayload.mockImplementation(mapping => ({ ...mapping, location: null }));

      const { save } = dialog();
      await save();

      expect(onSaved).toHaveBeenCalledWith(MAPPING);
    });

    it('should mark itself loading only while the write runs', async () => {
      const { loading, save } = dialog();

      const pending = save();
      expect(get(loading)).toBe(true);

      await pending;
      expect(get(loading)).toBe(false);
    });
  });

  describe('a write that does not land', () => {
    it('should keep the dialog open when the endpoint refuses', async () => {
      add.mockResolvedValue(false);

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(get(modelValue)).toBeDefined();
      expect(onSaved).not.toHaveBeenCalled();
    });

    it('should report a failure while adding as an add failure', async () => {
      add.mockRejectedValue(new Error('the backend is down'));

      const { save } = dialog();

      expect(await save()).toBe(false);
      expect(setMessage).toHaveBeenCalledWith({
        description: 'asset_management.cex_mapping.add_error::the backend is down',
      });
    });

    it('should report a failure while editing as an edit failure', async () => {
      set(editMode, true);
      edit.mockRejectedValue(new Error('the backend is down'));

      const { save } = dialog();
      await save();

      expect(setMessage).toHaveBeenCalledWith({
        description: 'asset_management.cex_mapping.edit_error::the backend is down',
      });
    });

    it('should stop loading so the user can try again', async () => {
      add.mockRejectedValue(new Error('boom'));

      const { loading, save } = dialog();
      await save();

      expect(get(loading)).toBe(false);
    });
  });
});
