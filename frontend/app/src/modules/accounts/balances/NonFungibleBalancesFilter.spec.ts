import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import NonFungibleBalancesFilter from '@/modules/accounts/balances/NonFungibleBalancesFilter.vue';
import { IgnoredAssetHandlingType, type IgnoredAssetsHandlingType } from '@/modules/assets/types';

const stubs = {
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean }, modelValue: { default: undefined, type: String } },
    template: '<button v-bind="$attrs" :disabled="disabled" :data-value="modelValue"><slot /></button>',
  },
  RuiButtonGroup: {
    emits: ['update:modelValue'],
    props: { modelValue: { default: undefined, type: String } },
    template: '<div data-testid="asset-filter-ignored" :data-selected="modelValue"><button v-for="value in [\'none\', \'exclude\', \'show_only\']" :key="value" :data-testid="\'filter-\' + value" @click="$emit(\'update:modelValue\', value)" /><slot /></div>',
  },
  RuiIcon: true,
  RuiTooltip: { template: '<div><slot name="activator" /></div>' },
  TableSelectionBar: {
    emits: ['clear', 'exit'],
    props: { count: { required: true, type: Number }, exitable: { default: false, type: Boolean } },
    template: '<div data-testid="selection-bar" :data-count="count"><button data-testid="selection-clear" @click="$emit(\'clear\')" /><button data-testid="selection-exit" @click="$emit(\'exit\')" /><slot /></div>',
  },
};

interface Props {
  selected?: string[];
  ignoredAssetsHandling?: IgnoredAssetsHandlingType;
  selectionMode?: boolean;
}

function createWrapper(props: Props = {}): VueWrapper<InstanceType<typeof NonFungibleBalancesFilter>> {
  return mount(NonFungibleBalancesFilter, {
    global: { stubs },
    props: {
      ignoredAssetsHandling: IgnoredAssetHandlingType.NONE,
      selected: [],
      selectionMode: false,
      ...props,
    },
  });
}

describe('modules/accounts/balances/NonFungibleBalancesFilter', () => {
  it('should offer selection and the ignored filter outside selection mode', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=nft-balances-select]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=asset-filter-ignored]').attributes('data-selected')).toBe(IgnoredAssetHandlingType.NONE);
    expect(wrapper.find('[data-testid=selection-bar]').exists()).toBe(false);
  });

  it('should enter selection mode from the select button', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=nft-balances-select]').trigger('click');

    expect(wrapper.emitted('update:selectionMode')).toEqual([[true]]);
  });

  it('should pass a filter change up', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=filter-exclude]').trigger('click');

    expect(wrapper.emitted('update:ignoredAssetsHandling')).toEqual([[IgnoredAssetHandlingType.EXCLUDE]]);
  });

  it('should show the selection bar with its count in selection mode', () => {
    const wrapper = createWrapper({ selected: ['a', 'b'], selectionMode: true });

    expect(wrapper.find('[data-testid=selection-bar]').attributes('data-count')).toBe('2');
    expect(wrapper.find('[data-testid=nft-balances-select]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=asset-filter-ignored]').exists()).toBe(false);
  });

  it('should disable both actions with nothing selected', () => {
    const wrapper = createWrapper({ selectionMode: true });

    expect(wrapper.find('[data-testid=nft-balances-ignore]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=nft-balances-unignore]').attributes('disabled')).toBeDefined();
  });

  it('should allow both actions with a selection and no ignored filter', () => {
    const wrapper = createWrapper({ selected: ['a'], selectionMode: true });

    expect(wrapper.find('[data-testid=nft-balances-ignore]').attributes('disabled')).toBeUndefined();
    expect(wrapper.find('[data-testid=nft-balances-unignore]').attributes('disabled')).toBeUndefined();
  });

  it('should not offer to ignore what the filter shows as already ignored', () => {
    const wrapper = createWrapper({ ignoredAssetsHandling: IgnoredAssetHandlingType.SHOW_ONLY, selected: ['a'], selectionMode: true });

    expect(wrapper.find('[data-testid=nft-balances-ignore]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=nft-balances-unignore]').attributes('disabled')).toBeUndefined();
  });

  it('should not offer to unignore what the filter excludes as ignored', () => {
    const wrapper = createWrapper({ ignoredAssetsHandling: IgnoredAssetHandlingType.EXCLUDE, selected: ['a'], selectionMode: true });

    expect(wrapper.find('[data-testid=nft-balances-ignore]').attributes('disabled')).toBeUndefined();
    expect(wrapper.find('[data-testid=nft-balances-unignore]').attributes('disabled')).toBeDefined();
  });

  it('should ask to ignore or unignore the selection', async () => {
    const wrapper = createWrapper({ selected: ['a'], selectionMode: true });
    await wrapper.find('[data-testid=nft-balances-ignore]').trigger('click');
    await wrapper.find('[data-testid=nft-balances-unignore]').trigger('click');

    expect(wrapper.emitted('mass-ignore')).toEqual([[true], [false]]);
  });

  it('should clear the selection but stay in selection mode', async () => {
    const wrapper = createWrapper({ selected: ['a'], selectionMode: true });
    await wrapper.find('[data-testid=selection-clear]').trigger('click');

    expect(wrapper.emitted('update:selected')).toEqual([[[]]]);
    expect(wrapper.emitted('update:selectionMode')).toBeUndefined();
  });

  it('should clear the selection and leave selection mode on exit', async () => {
    const wrapper = createWrapper({ selected: ['a'], selectionMode: true });
    await wrapper.find('[data-testid=selection-exit]').trigger('click');

    expect(wrapper.emitted('update:selected')).toEqual([[[]]]);
    expect(wrapper.emitted('update:selectionMode')).toEqual([[false]]);
  });
});
