import type { PriceOracle } from '@/modules/settings/types/price-oracle';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import OracleCacheFormDialog from '@/modules/assets/prices/components/oracle/OracleCacheFormDialog.vue';

const valueField = {
  emits: ['update:modelValue'],
  inheritAttrs: false,
  props: { disabled: { default: false, type: Boolean }, modelValue: { default: '', type: String } },
  template: '<input :data-testid="$attrs[\'data-testid\']" :value="modelValue" :disabled="disabled" @input="$emit(\'update:modelValue\', $event.target.value)" />',
};

const stubs = {
  AssetSelect: valueField,
  BigDialog: {
    emits: ['confirm', 'cancel'],
    props: {
      action: { default: undefined, type: Object },
      display: { default: false, type: Boolean },
      loading: { default: false, type: Boolean },
      title: { required: true, type: String },
    },
    template: `<div data-testid="dialog" :data-display="display" :data-loading="loading" :data-title="title">
      <slot />
      <button data-testid="dialog-confirm" :disabled="action?.disabled" @click="$emit('confirm')">{{ action?.primary }}</button>
      <button data-testid="dialog-cancel" @click="$emit('cancel')" />
    </div>`,
  },
  RuiAutoComplete: valueField,
};

interface Models {
  open?: boolean;
  source?: PriceOracle;
  fromAsset?: string;
  toAsset?: string;
  loading?: boolean;
}

function createWrapper(models: Models = {}): VueWrapper<InstanceType<typeof OracleCacheFormDialog>> {
  return mount(OracleCacheFormDialog, {
    global: { stubs },
    props: {
      fromAsset: 'ETH',
      open: true,
      source: 'coingecko',
      sourceOptions: [{ identifier: 'coingecko', label: 'CoinGecko' }, { identifier: 'cryptocompare', label: 'CryptoCompare' }],
      toAsset: 'USD',
      ...models,
    },
  });
}

describe('modules/assets/prices/components/oracle/OracleCacheFormDialog', () => {
  it('should show while open, with the add title and create action', () => {
    const wrapper = createWrapper();
    const dialog = wrapper.find('[data-testid=dialog]');

    expect(dialog.attributes('data-display')).toBe('true');
    expect(dialog.attributes('data-title')).toBe('oracle_prices.cache.add');
    expect(wrapper.find('[data-testid=dialog-confirm]').text()).toBe('oracle_prices.cache.dialog.create');
  });

  it('should ask to create the cache on confirm', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=dialog-confirm]').trigger('click');

    expect(wrapper.emitted('confirm')).toEqual([[]]);
  });

  it('should close on cancel', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=dialog-cancel]').trigger('click');

    expect(wrapper.emitted('update:open')).toEqual([[false]]);
    expect(wrapper.emitted('confirm')).toBeUndefined();
  });

  it.each([
    ['from', { fromAsset: '' }],
    ['to', { toAsset: '' }],
  ])('should not allow creating without a %s asset', (_, models) => {
    const wrapper = createWrapper(models);

    expect(wrapper.find('[data-testid=dialog-confirm]').attributes('disabled')).toBeDefined();
  });

  it('should allow creating once both assets are picked', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=dialog-confirm]').attributes('disabled')).toBeUndefined();
  });

  it('should pass the picked source and assets back up', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=oracle-cache-source]').setValue('cryptocompare');
    await wrapper.find('[data-testid=oracle-cache-from-asset]').setValue('BTC');
    await wrapper.find('[data-testid=oracle-cache-to-asset]').setValue('EUR');

    expect(wrapper.emitted('update:source')).toEqual([['cryptocompare']]);
    expect(wrapper.emitted('update:fromAsset')).toEqual([['BTC']]);
    expect(wrapper.emitted('update:toAsset')).toEqual([['EUR']]);
  });

  it('should lock the fields while the cache is being created', () => {
    const wrapper = createWrapper({ loading: true });

    expect(wrapper.find('[data-testid=dialog]').attributes('data-loading')).toBe('true');
    for (const id of ['oracle-cache-source', 'oracle-cache-from-asset', 'oracle-cache-to-asset'])
      expect(wrapper.find(`[data-testid=${id}]`).attributes('disabled')).toBeDefined();
  });
});
