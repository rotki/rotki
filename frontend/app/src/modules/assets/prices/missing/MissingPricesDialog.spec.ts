import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MissingPricesDialog from '@/modules/assets/prices/missing/MissingPricesDialog.vue';

const refreshPrice = vi.fn<(asset: string) => Promise<void>>();

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: (): Record<string, unknown> => ({ refreshPrice }),
}));

function createWrapper(identifiers: string[]): VueWrapper<InstanceType<typeof MissingPricesDialog>> {
  return mount(MissingPricesDialog, {
    global: {
      stubs: {
        AssetDetails: { props: ['asset'], template: '<div class="asset">{{ asset }}</div>' },
        LatestPriceFormDialog: {
          emits: ['refresh', 'update:open'],
          name: 'LatestPriceFormDialog',
          props: {
            disableFromAsset: { type: Boolean },
            open: { type: Boolean },
            prefill: { default: null, type: Object },
          },
          template: '<div class="form-dialog" />',
        },
        RouterLink: { template: '<div><slot /></div>' },
        RuiCard: { template: '<div><slot name="header" /><slot /><slot name="footer" /></div>' },
        RuiDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' },
      },
    },
    props: { identifiers, open: true },
  });
}

describe('modules/assets/prices/missing/MissingPricesDialog', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    refreshPrice.mockReset().mockResolvedValue(undefined);
  });

  it('should list a row per asset missing a price', () => {
    const wrapper = createWrapper(['ETH', 'BTC']);

    expect(wrapper.findAll('.asset').map(asset => asset.text())).toEqual(['ETH', 'BTC']);
    expect(wrapper.findAll('[data-testid=missing-price-add]')).toHaveLength(2);
    expect(wrapper.find('[data-testid=missing-prices-empty]').exists()).toBe(false);
  });

  it('should show the resolved state when nothing is left', () => {
    const wrapper = createWrapper([]);

    expect(wrapper.find('[data-testid=missing-prices-list]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=missing-prices-empty]').exists()).toBe(true);
  });

  it('should open a pre-filled add form for the picked asset and re-price only it once saved', async () => {
    const wrapper = createWrapper(['ETH', 'BTC']);

    await wrapper.findAll('[data-testid=missing-price-add]')[1].trigger('click');

    const form = wrapper.findComponent({ name: 'LatestPriceFormDialog' });
    expect(form.props('disableFromAsset')).toBe(true);
    expect(form.props('prefill')).toMatchObject({ fromAsset: 'BTC', price: '' });

    form.vm.$emit('refresh');
    await flushPromises();

    expect(refreshPrice).toHaveBeenCalledExactlyOnceWith('BTC');
    expect(wrapper.findComponent({ name: 'LatestPriceFormDialog' }).exists()).toBe(false);
  });
});
