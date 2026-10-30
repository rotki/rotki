import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { mount } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { flatLocationTree } from '@/modules/locations/flat-location-tree';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import '@test/i18n';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({
    getBlockchainRedirectLink: (): undefined => undefined,
    getChainImageUrl: (): string => '',
    getChainName: (chain: string): string => (chain === 'binance_sc' ? 'Binance Smart Chain' : chain),
    matchChain: (id: string): string | undefined => (id === 'binance_sc' ? id : undefined),
  }),
}));

/** Renders the selection slot for the chosen option, which the shared stub leaves out, as the real one does: only once an option matches. */
const AutoCompleteStub = defineComponent({
  props: {
    modelValue: { default: '', type: String },
    options: { default: (): unknown[] => [], type: Array },
  },
  setup: (props, { slots }) => (): VNode => {
    const item = props.options.find(option => typeof option === 'object' && option !== null && Reflect.get(option, 'identifier') === props.modelValue);
    return h('div', item ? slots.selection?.({ item }) : undefined);
  },
});

describe('locationSelector', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    useLocationTreeStore().setNodes([
      node('total', null, 'Total'),
      node('banks', 'total', 'Banks'),
      node('exchanges', 'total', 'Exchanges'),
      node('custom:ing-bank', 'banks', 'ING', { isBuiltin: false }),
      node('custom:ing-exchange', 'exchanges', 'ING', { isBuiltin: false }),
      node('custom:luno', 'exchanges', 'Luno', { isBuiltin: false }),
    ]);
  });

  function selection(modelValue: string): string {
    const wrapper = mount(LocationSelector, {
      global: { plugins: [pinia], stubs: { LocationIcon: true, RuiAutoComplete: AutoCompleteStub } },
      props: { modelValue },
    });
    return wrapper.find('[data-testid=location-selection]').text();
  }

  it('should show the path of a chosen location whose name another location shares', () => {
    expect(selection('custom:ing-bank')).toBe('Banks › ING');
  });

  it('should show just the name of a chosen location with a name of its own', () => {
    expect(selection('custom:luno')).toBe('Luno');
  });

  it('should show the display name of a chosen location, not its raw tree name, on a flat tree', () => {
    useLocationStore().allLocations = { coinbaseprime: { label: 'Coinbase Prime' } };
    useLocationTreeStore().setNodes(flatLocationTree({ coinbaseprime: {} }));

    expect(selection('coinbaseprime')).toBe('Coinbase Prime');
  });

  it('should name a chosen chain by its chain name, as the rest of the app does', () => {
    useLocationStore().allLocations = { 'binance sc': { label: 'Binance sc' } };
    useLocationTreeStore().setNodes(flatLocationTree({ 'binance sc': {} }));

    expect(selection('binance sc')).toBe('Binance Smart Chain');
  });

  function mountSelector(modelValue: string): ReturnType<typeof mount> {
    return mount(LocationSelector, {
      global: { plugins: [pinia], stubs: { LocationIcon: true, RuiAutoComplete: AutoCompleteStub } },
      props: { modelValue },
    });
  }

  function offered(wrapper: ReturnType<typeof mount>): unknown[] {
    return wrapper.findComponent(AutoCompleteStub).props('options') ?? [];
  }

  it('should keep the same options when picking between assignable locations', async () => {
    const wrapper = mountSelector('custom:luno');
    const before = offered(wrapper);

    await wrapper.setProps({ modelValue: 'custom:ing-bank' });

    expect(offered(wrapper)).toBe(before);
  });

  it('should keep a custom value while the location data is still loading', async () => {
    const tree = useLocationTreeStore();
    const nodes = tree.nodes;
    tree.setNodes([]);
    const wrapper = mountSelector('custom:luno');

    useLocationStore().allLocations = { kraken: { isExchange: true, label: 'Kraken' } };
    await nextTick();
    tree.setNodes(nodes);
    await nextTick();

    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should clear a value the selector stops offering', async () => {
    const wrapper = mountSelector('custom:luno');

    await wrapper.setProps({ excludes: ['custom:luno'] });

    expect(wrapper.emitted('update:modelValue')).toEqual([['']]);
  });

  it('should still offer an archived current value, and drop it once another is picked', async () => {
    useLocationTreeStore().setNodes([
      node('total', null, 'Total'),
      node('exchanges', 'total', 'Exchanges'),
      node('custom:luno', 'exchanges', 'Luno', { isBuiltin: false }),
      node('custom:closed', 'exchanges', 'Closed', { isActive: false, isBuiltin: false }),
    ]);
    const identifiers = (wrapper: ReturnType<typeof mount>): unknown[] =>
      offered(wrapper).map(option => Reflect.get(new Object(option), 'identifier'));
    const wrapper = mountSelector('custom:closed');
    expect(identifiers(wrapper)).toContain('custom:closed');

    await wrapper.setProps({ modelValue: 'custom:luno' });

    expect(identifiers(wrapper)).not.toContain('custom:closed');
  });
});
