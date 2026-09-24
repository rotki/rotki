import type { LocationFormData } from '@/modules/locations/location-form';
import type { useLocationManagement } from '@/modules/locations/use-location-management';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import LocationFormDialog from '@/modules/locations/components/LocationFormDialog.vue';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import '@test/i18n';

type Management = ReturnType<typeof useLocationManagement>;

const { createLocation, editLocation, previewEdit, removeImage, setMessage, show, uploadImage } = vi.hoisted(() => ({
  createLocation: vi.fn<Management['createLocation']>(),
  editLocation: vi.fn<Management['editLocation']>(),
  previewEdit: vi.fn<Management['previewEdit']>(),
  removeImage: vi.fn<Management['removeImage']>(),
  setMessage: vi.fn(),
  show: vi.fn(),
  uploadImage: vi.fn<Management['uploadImage']>(),
}));

vi.mock('@/modules/locations/use-location-management', () => ({
  useLocationManagement: (): Partial<Management> => ({ createLocation, editLocation, previewEdit, removeImage, uploadImage }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

const BigDialogStub = defineComponent({
  emits: ['cancel', 'confirm'],
  setup: (_props, { slots }) => (): VNode => h('div', slots.default?.()),
});

const LocationSelectorStub = defineComponent({
  emits: ['update:modelValue'],
  props: { items: { default: (): string[] => [], type: Array }, modelValue: { default: '', type: String } },
  setup: props => (): VNode => h('div', { 'data-items': props.items.join(',') }),
});

const LocationImageFieldStub = defineComponent({
  emits: ['update:modelValue'],
  setup: () => (): VNode => h('div'),
});

const ing = node('custom:ing', 'banks', 'ING', { icon: 'lu-landmark', image: 'ing.png', isBuiltin: false });

describe('locationFormDialog', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof LocationFormDialog>>;

  function createWrapper(modelValue: LocationFormData): VueWrapper<InstanceType<typeof LocationFormDialog>> {
    return mount(LocationFormDialog, {
      global: {
        plugins: [pinia],
        stubs: {
          BigDialog: BigDialogStub,
          LocationImageField: LocationImageFieldStub,
          LocationSelector: LocationSelectorStub,
        },
      },
      props: { modelValue },
    });
  }

  async function confirm(): Promise<void> {
    wrapper.findComponent(BigDialogStub).vm.$emit('confirm');
    await flushPromises();
  }

  async function chooseImage(image: File | null): Promise<void> {
    wrapper.findComponent(LocationImageFieldStub).vm.$emit('update:modelValue', image);
    await flushPromises();
  }

  async function chooseParent(identifier: string): Promise<void> {
    wrapper.findComponent(LocationSelectorStub).vm.$emit('update:modelValue', identifier);
    await flushPromises();
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    useLocationTreeStore().setNodes([
      node('total', null, 'Total'),
      node('banks', 'total', 'Banks'),
      node('other', 'total', 'Other'),
      ing,
      node('custom:savings', 'custom:ing', 'Savings', { isBuiltin: false }),
    ]);
    editLocation.mockResolvedValue(ok({ location: ing, newPath: [], oldPath: [] }));
  });

  it('should create the location below the chosen parent with the picked icon', async () => {
    createLocation.mockResolvedValue(ok(ing));
    wrapper = createWrapper({ mode: 'add', parentIdentifier: 'banks' });

    await wrapper.find('[data-testid=location-form-name] input').setValue('  DKB ');
    await wrapper.find('[data-testid=location-icon-lu-vault]').trigger('click');
    await confirm();

    expect(createLocation).toHaveBeenCalledExactlyOnceWith({ icon: 'lu-vault', name: 'DKB', parentIdentifier: 'banks' });
    expect(wrapper.emitted('created')).toEqual([[ing]]);
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });

  it('should not save without a name', async () => {
    wrapper = createWrapper({ mode: 'add', parentIdentifier: 'banks' });
    await confirm();
    expect(createLocation).not.toHaveBeenCalled();
  });

  it('should not offer the location itself or its descendants as parent', () => {
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    expect(wrapper.find('[data-testid=location-form-parent]').attributes('data-items')).toBe('total,banks,other');
  });

  it('should save a rename directly, sending only what changed', async () => {
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    await wrapper.find('[data-testid=location-form-name] input').setValue('ING DiBa');
    await confirm();

    expect(previewEdit).not.toHaveBeenCalled();
    expect(editLocation).toHaveBeenCalledExactlyOnceWith('custom:ing', { name: 'ING DiBa' });
  });

  it('should only move a location once the new path is confirmed', async () => {
    previewEdit.mockResolvedValue(ok({ location: ing, newPath: ['Total', 'Other', 'ING'], oldPath: ['Total', 'Banks', 'ING'] }));
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    await chooseParent('other');
    await confirm();

    expect(previewEdit).toHaveBeenCalledExactlyOnceWith('custom:ing', { parentIdentifier: 'other' });
    expect(show).toHaveBeenCalledWith(
      expect.objectContaining({ message: expect.stringContaining('Banks › ING'), type: 'info' }),
      expect.any(Function),
    );
    expect(editLocation).not.toHaveBeenCalled();
    await show.mock.calls[0][1]();
    expect(editLocation).toHaveBeenCalledExactlyOnceWith('custom:ing', { parentIdentifier: 'other' });
  });

  it('should upload a chosen image only once the new location exists', async () => {
    const created = node('custom:dkb', 'banks', 'DKB', { isBuiltin: false });
    const file = new File(['png'], 'dkb.png');
    createLocation.mockResolvedValue(ok(created));
    uploadImage.mockResolvedValue(ok('dkb.png'));
    wrapper = createWrapper({ mode: 'add', parentIdentifier: 'banks' });
    await wrapper.find('[data-testid=location-form-name] input').setValue('DKB');
    await chooseImage(file);
    expect(uploadImage).not.toHaveBeenCalled();

    await confirm();

    expect(uploadImage).toHaveBeenCalledExactlyOnceWith('custom:dkb', file);
    expect(createLocation.mock.invocationCallOrder[0]).toBeLessThan(uploadImage.mock.invocationCallOrder[0]);
    expect(wrapper.emitted('saved')).toEqual([['custom:dkb']]);
  });

  it('should remove the stored image on save without editing anything else', async () => {
    removeImage.mockResolvedValue(ok(true));
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    await chooseImage(null);
    expect(removeImage).not.toHaveBeenCalled();

    await confirm();

    expect(editLocation).not.toHaveBeenCalled();
    expect(removeImage).toHaveBeenCalledExactlyOnceWith('custom:ing');
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });

  it('should keep the dialog open and show why a save was refused', async () => {
    createLocation.mockResolvedValue(err('A location named DKB already exists at the same level'));
    wrapper = createWrapper({ mode: 'add', parentIdentifier: 'banks' });
    await wrapper.find('[data-testid=location-form-name] input').setValue('DKB');
    await confirm();

    expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ description: 'A location named DKB already exists at the same level' }));
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should keep a created location and close when only its image upload fails', async () => {
    const created = node('custom:dkb', 'banks', 'DKB', { isBuiltin: false });
    createLocation.mockResolvedValue(ok(created));
    uploadImage.mockResolvedValue(err('Unsupported image type'));
    wrapper = createWrapper({ mode: 'add', parentIdentifier: 'banks' });
    await wrapper.find('[data-testid=location-form-name] input').setValue('DKB');
    await chooseImage(new File(['gif'], 'dkb.gif'));

    await confirm();

    expect(setMessage).toHaveBeenCalledExactlyOnceWith({ description: 'Unsupported image type', title: 'location_manager.image.error' });
    expect(wrapper.emitted('created')).toEqual([[created]]);
    expect(wrapper.emitted('saved')).toEqual([['custom:dkb']]);
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });

  it('should not ask to confirm a move whose preview was refused', async () => {
    previewEdit.mockResolvedValue(err('Location custom:ing can not be moved below itself'));
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    await chooseParent('other');

    await confirm();

    expect(setMessage).toHaveBeenCalledExactlyOnceWith({ description: 'Location custom:ing can not be moved below itself', title: 'location_manager.form.error' });
    expect(show).not.toHaveBeenCalled();
    expect(editLocation).not.toHaveBeenCalled();
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should keep the dialog open and skip the image when an edit is refused', async () => {
    editLocation.mockResolvedValue(err('A location named Qonto already exists at the same level'));
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    await wrapper.find('[data-testid=location-form-name] input').setValue('Qonto');
    await chooseImage(null);

    await confirm();

    expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ description: 'A location named Qonto already exists at the same level' }));
    expect(removeImage).not.toHaveBeenCalled();
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should load the next location into the form when the dialog is reused', async () => {
    const savings = node('custom:savings', 'custom:ing', 'Savings', { isBuiltin: false });
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    await wrapper.find('[data-testid=location-form-name] input').setValue('typed but not saved');

    await wrapper.setProps({ modelValue: { location: savings, mode: 'edit' } });

    expect(wrapper.find<HTMLInputElement>('[data-testid=location-form-name] input').element.value).toBe('Savings');
  });
});
