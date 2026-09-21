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

const { createLocation, editLocation, previewEdit, setMessage, show } = vi.hoisted(() => ({
  createLocation: vi.fn<Management['createLocation']>(),
  editLocation: vi.fn<Management['editLocation']>(),
  previewEdit: vi.fn<Management['previewEdit']>(),
  setMessage: vi.fn(),
  show: vi.fn(),
}));

vi.mock('@/modules/locations/use-location-management', () => ({
  useLocationManagement: (): Partial<Management> => ({ createLocation, editLocation, previewEdit }),
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

const ing = node('custom:ing', 'banks', 'ING', { icon: 'lu-landmark', isBuiltin: false });

describe('locationFormDialog', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof LocationFormDialog>>;

  function createWrapper(modelValue: LocationFormData): VueWrapper<InstanceType<typeof LocationFormDialog>> {
    return mount(LocationFormDialog, {
      global: {
        plugins: [pinia],
        stubs: {
          BigDialog: BigDialogStub,
          LocationImageField: true,
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
    expect(show).toHaveBeenCalledWith(expect.objectContaining({ message: expect.stringContaining('Banks › ING') }), expect.any(Function));
    expect(editLocation).not.toHaveBeenCalled();
    await show.mock.calls[0][1]();
    expect(editLocation).toHaveBeenCalledExactlyOnceWith('custom:ing', { parentIdentifier: 'other' });
  });

  it('should keep the dialog open and show why a save was refused', async () => {
    createLocation.mockResolvedValue(err('A location named DKB already exists at the same level'));
    wrapper = createWrapper({ mode: 'add', parentIdentifier: 'banks' });
    await wrapper.find('[data-testid=location-form-name] input').setValue('DKB');
    await confirm();

    expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ description: 'A location named DKB already exists at the same level' }));
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });
});
