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

const { createLocation, editLocation, previewEdit, removeImage, uploadImage } = vi.hoisted(() => ({
  createLocation: vi.fn<Management['createLocation']>(),
  editLocation: vi.fn<Management['editLocation']>(),
  previewEdit: vi.fn<Management['previewEdit']>(),
  removeImage: vi.fn<Management['removeImage']>(),
  uploadImage: vi.fn<Management['uploadImage']>(),
}));

vi.mock('@/modules/locations/use-location-management', () => ({
  useLocationManagement: (): Partial<Management> => ({
    createLocation,
    editLocation,
    previewEdit,
    removeImage,
    uploadImage,
  }),
}));

const BigDialogStub = defineComponent({
  emits: ['cancel', 'confirm'],
  props: { action: { default: undefined, type: Object }, loading: { default: false, type: Boolean } },
  setup: (props, { slots }) => (): VNode => h('div', { 'data-loading': String(props.loading), 'data-primary': props.action?.primary }, slots.default?.()),
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

  /**
   * Mounts the dialog; with `synced` the parent's `v-model` follows its updates, as when the
   * dialog switches itself from adding to editing.
   */
  function createWrapper(modelValue: LocationFormData, synced = false): VueWrapper<InstanceType<typeof LocationFormDialog>> {
    return mount(LocationFormDialog, {
      global: {
        plugins: [pinia],
        stubs: {
          BigDialog: BigDialogStub,
          LocationImageField: LocationImageFieldStub,
          LocationSelector: LocationSelectorStub,
        },
      },
      props: {
        modelValue,
        'onUpdate:modelValue': synced
          ? async (value: LocationFormData | undefined): Promise<void> => wrapper.setProps({ modelValue: value })
          : undefined,
      },
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
    expect(wrapper.emitted('saved')).toEqual([[ing.identifier]]);
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

  it('should offer the parents in tree order, each below its own parent', () => {
    useLocationTreeStore().setNodes([...useLocationTreeStore().nodes, node('custom:amex', 'other', 'Amex', { isBuiltin: false })]);
    wrapper = createWrapper({ mode: 'add', parentIdentifier: 'banks' });
    expect(wrapper.find('[data-testid=location-form-parent]').attributes('data-items'))
      .toBe('total,banks,custom:ing,custom:savings,other,custom:amex');
  });

  it('should save a rename directly, sending only what changed', async () => {
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    await wrapper.find('[data-testid=location-form-name] input').setValue('ING DiBa');
    await confirm();

    expect(previewEdit).not.toHaveBeenCalled();
    expect(editLocation).toHaveBeenCalledExactlyOnceWith('custom:ing', { name: 'ING DiBa' });
  });

  it('should show a move in the form and only save it on a second save', async () => {
    previewEdit.mockResolvedValue(ok({ location: ing, newPath: ['Total', 'Other', 'ING'], oldPath: ['Total', 'Banks', 'ING'] }));
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    await chooseParent('other');
    await confirm();

    expect(previewEdit).toHaveBeenCalledExactlyOnceWith('custom:ing', { parentIdentifier: 'other' });
    expect(wrapper.find('[data-testid=location-form-move]').text()).toContain('location_manager.move.message::Other › ING, Banks › ING');
    expect(wrapper.findComponent(BigDialogStub).attributes('data-primary')).toBe('location_manager.move.confirm');
    expect(editLocation).not.toHaveBeenCalled();

    await confirm();
    expect(previewEdit).toHaveBeenCalledOnce();
    expect(editLocation).toHaveBeenCalledExactlyOnceWith('custom:ing', { parentIdentifier: 'other' });
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });

  it('should check the move again when the parent changes after it was shown', async () => {
    previewEdit.mockResolvedValue(ok({ location: ing, newPath: ['Total', 'Other', 'ING'], oldPath: ['Total', 'Banks', 'ING'] }));
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    await chooseParent('other');
    await confirm();
    await chooseParent('total');

    expect(wrapper.find('[data-testid=location-form-move]').exists()).toBe(false);
    await confirm();
    expect(previewEdit).toHaveBeenLastCalledWith('custom:ing', { parentIdentifier: 'total' });
    expect(editLocation).not.toHaveBeenCalled();
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

    expect(wrapper.find('[data-testid=location-form-error]').text()).toContain('A location named DKB already exists at the same level');
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should keep a created location and go on editing it when only its image upload fails', async () => {
    const created = node('custom:dkb', 'banks', 'DKB', { isBuiltin: false });
    createLocation.mockResolvedValue(ok(created));
    uploadImage.mockResolvedValue(err('Unsupported image type'));
    wrapper = createWrapper({ mode: 'add', parentIdentifier: 'banks' });
    await wrapper.find('[data-testid=location-form-name] input').setValue('DKB');
    await chooseImage(new File(['gif'], 'dkb.gif'));

    await confirm();

    expect(wrapper.find('[data-testid=location-form-image-error]').text()).toContain('Unsupported image type');
    expect(wrapper.emitted('saved')).toEqual([['custom:dkb']]);
    expect(wrapper.emitted('update:modelValue')).toEqual([[{ location: created, mode: 'edit' }]]);
  });

  it('should keep the chosen image of a created location for the retry', async () => {
    const created = node('custom:dkb', 'banks', 'DKB', { isBuiltin: false });
    const file = new File(['gif'], 'dkb.gif');
    createLocation.mockResolvedValue(ok(created));
    uploadImage.mockResolvedValueOnce(err('Unsupported image type')).mockResolvedValueOnce(ok('dkb.png'));
    wrapper = createWrapper({ mode: 'add', parentIdentifier: 'banks' }, true);
    await wrapper.find('[data-testid=location-form-name] input').setValue('DKB');
    await chooseImage(file);
    await confirm();
    useLocationTreeStore().upsertNode(created);

    expect(wrapper.find('[data-testid=location-form-image-error]').exists()).toBe(true);
    await confirm();
    expect(createLocation).toHaveBeenCalledOnce();
    expect(uploadImage).toHaveBeenLastCalledWith('custom:dkb', file);
    expect(uploadImage).toHaveBeenCalledTimes(2);
  });

  it('should retry only the image of a saved edit on the next save', async () => {
    const file = new File(['gif'], 'ing.gif');
    const renamed = { ...ing, name: 'ING DiBa' };
    editLocation.mockResolvedValue(ok({ location: renamed, newPath: [], oldPath: [] }));
    uploadImage.mockResolvedValueOnce(err('Unsupported image type')).mockResolvedValueOnce(ok('ing.png'));
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    await wrapper.find('[data-testid=location-form-name] input').setValue('ING DiBa');
    await chooseImage(file);
    await confirm();

    expect(wrapper.find('[data-testid=location-form-image-error]').exists()).toBe(true);
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();

    useLocationTreeStore().upsertNode(renamed);
    await confirm();
    expect(editLocation).toHaveBeenCalledOnce();
    expect(uploadImage).toHaveBeenCalledTimes(2);
    expect(wrapper.find('[data-testid=location-form-image-error]').exists()).toBe(false);
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });

  it('should not show a move whose check was refused', async () => {
    previewEdit.mockResolvedValue(err('Location custom:ing can not be moved below itself'));
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    await chooseParent('other');

    await confirm();

    expect(wrapper.find('[data-testid=location-form-error]').text()).toContain('Location custom:ing can not be moved below itself');
    expect(wrapper.find('[data-testid=location-form-move]').exists()).toBe(false);
    expect(editLocation).not.toHaveBeenCalled();
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should keep the dialog open and skip the image when an edit is refused', async () => {
    editLocation.mockResolvedValue(err('A location named Qonto already exists at the same level'));
    wrapper = createWrapper({ location: ing, mode: 'edit' });
    await wrapper.find('[data-testid=location-form-name] input').setValue('Qonto');
    await chooseImage(null);

    await confirm();

    expect(wrapper.find('[data-testid=location-form-error]').text()).toContain('A location named Qonto already exists at the same level');
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
