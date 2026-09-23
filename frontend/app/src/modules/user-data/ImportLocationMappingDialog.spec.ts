import type { ImportLocationResolution } from '@/modules/user-data/use-import-data-api';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import ImportLocationMappingDialog from '@/modules/user-data/ImportLocationMappingDialog.vue';
import '@test/i18n';

const BigDialogStub = defineComponent({
  emits: ['cancel', 'confirm'],
  props: { action: { default: undefined, type: Object } },
  setup: (_props, { slots }) => (): VNode => h('div', slots.default?.()),
});

const LocationSelectorStub = defineComponent({
  emits: ['update:modelValue'],
  props: { items: { default: (): string[] => [], type: Array }, modelValue: { default: '', type: String } },
  setup: props => (): VNode => h('div', { 'data-items': props.items.join(',') }),
});

const LocationFormDialogStub = defineComponent({
  emits: ['created', 'update:modelValue'],
  props: { modelValue: { default: undefined, type: Object } },
  setup: () => (): VNode => h('div'),
});

const ing: ImportLocationResolution = { candidates: ['custom:a', 'custom:b'], location: null, status: 'ambiguous', value: 'ING' };
const luno: ImportLocationResolution = { candidates: [], location: null, status: 'unresolved', value: 'luno' };

describe('importLocationMappingDialog', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof ImportLocationMappingDialog>>;

  function createWrapper(resolutions: ImportLocationResolution[]): VueWrapper<InstanceType<typeof ImportLocationMappingDialog>> {
    return mount(ImportLocationMappingDialog, {
      global: {
        plugins: [pinia],
        stubs: { BigDialog: BigDialogStub, LocationFormDialog: LocationFormDialogStub, LocationSelector: LocationSelectorStub },
      },
      props: { resolutions },
    });
  }

  function choose(index: number, location: string): void {
    wrapper.findAllComponents(LocationSelectorStub)[index].vm.$emit('update:modelValue', location);
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  it('should offer only the candidates of an ambiguous value', () => {
    wrapper = createWrapper([ing, luno]);
    const selectors = wrapper.findAllComponents(LocationSelectorStub);
    expect(selectors[0].attributes('data-items')).toBe('custom:a,custom:b');
    expect(selectors[1].attributes('data-items')).toBe('');
  });

  it('should only import once every value has a location', async () => {
    wrapper = createWrapper([ing, luno]);
    const action = (): Record<string, unknown> | undefined => wrapper.findComponent(BigDialogStub).props('action');

    choose(0, 'custom:b');
    await nextTick();
    expect(action()?.disabled).toBe(true);
    wrapper.findComponent(BigDialogStub).vm.$emit('confirm');
    expect(wrapper.emitted('confirm')).toBeUndefined();

    choose(1, 'external');
    await nextTick();
    expect(action()?.disabled).toBe(false);
    await wrapper.find('[data-testid=import-location-save-aliases] input').setValue(false);
    wrapper.findComponent(BigDialogStub).vm.$emit('confirm');
    expect(wrapper.emitted('confirm')).toEqual([[{ mappings: { ING: 'custom:b', luno: 'external' }, saveAsAliases: false }]]);
  });

  it('should choose a location created for a value', async () => {
    wrapper = createWrapper([luno]);
    await wrapper.find('[data-testid=import-location-create]').trigger('click');
    expect(wrapper.findComponent(LocationFormDialogStub).props('modelValue')).toEqual({ mode: 'add', name: 'luno', parentIdentifier: '' });

    wrapper.findComponent(LocationFormDialogStub).vm.$emit('created', node('custom:luno', 'exchanges', 'luno', { isBuiltin: false }));
    await nextTick();
    wrapper.findComponent(BigDialogStub).vm.$emit('confirm');
    expect(wrapper.emitted('confirm')).toEqual([[{ mappings: { luno: 'custom:luno' }, saveAsAliases: true }]]);
  });

  it('should offer a location created for an ambiguous value next to its candidates', async () => {
    wrapper = createWrapper([ing]);
    await wrapper.find('[data-testid=import-location-create]').trigger('click');
    wrapper.findComponent(LocationFormDialogStub).vm.$emit('created', node('custom:c', 'total', 'ING', { isBuiltin: false }));
    await nextTick();

    const selector = wrapper.findComponent(LocationSelectorStub);
    expect(selector.attributes('data-items')).toBe('custom:a,custom:b,custom:c');
    expect(selector.props('modelValue')).toBe('custom:c');
  });
});
