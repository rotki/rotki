import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { mount } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import '@test/i18n';

/** A tree holding one location below the total, named by its identifier. */
function belowTotal(identifier: string): ReturnType<typeof node>[] {
  return [node('total', null, 'Total'), node(identifier, 'total', identifier)];
}

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
    itemHeight: { default: undefined, type: Number },
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

  it('should show the display name of a chosen location, not the identifier the tree names it by', () => {
    useLocationStore().allLocations = { coinbaseprime: { label: 'Coinbase Prime' } };
    useLocationTreeStore().setNodes(belowTotal('coinbaseprime'));

    expect(selection('coinbaseprime')).toBe('Coinbase Prime');
  });

  it('should name a chosen chain by its chain name, as the rest of the app does', () => {
    useLocationStore().allLocations = { 'binance sc': { label: 'Binance sc' } };
    useLocationTreeStore().setNodes(belowTotal('binance sc'));

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

  describe('item height', () => {
    function itemHeight(props: { dense?: boolean } = {}): unknown {
      const wrapper = mount(LocationSelector, {
        global: { plugins: [pinia], stubs: { LocationIcon: true, RuiAutoComplete: AutoCompleteStub } },
        props: { modelValue: '', ...props },
      });
      return wrapper.findComponent(AutoCompleteStub).props('itemHeight');
    }

    function useSingleLocationTree(): void {
      useLocationStore().allLocations = { kraken: { isExchange: true, label: 'Kraken' } };
      useLocationTreeStore().setNodes(belowTotal('kraken'));
    }

    it('should use the single-line height when no option has a path', () => {
      useSingleLocationTree();
      expect(itemHeight()).toBe(52);
    });

    it('should use the dense single-line height when no option has a path', () => {
      useSingleLocationTree();
      expect(itemHeight({ dense: true })).toBe(36);
    });

    it('should make every row tall enough for a path line when one option has a path', () => {
      expect(itemHeight()).toBe(64);
    });

    it('should make every dense row tall enough for a path line when one option has a path', () => {
      expect(itemHeight({ dense: true })).toBe(48);
    });
  });

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
