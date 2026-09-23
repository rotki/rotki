import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { mount } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import '@test/i18n';

/** Renders the selection slot for the chosen option, which the shared stub leaves out. */
const AutoCompleteStub = defineComponent({
  props: {
    modelValue: { default: '', type: String },
    options: { default: (): unknown[] => [], type: Array },
  },
  setup: (props, { slots }) => (): VNode =>
    h('div', slots.selection?.({
      item: props.options.find(option => typeof option === 'object' && option !== null && Reflect.get(option, 'identifier') === props.modelValue),
    })),
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
});
