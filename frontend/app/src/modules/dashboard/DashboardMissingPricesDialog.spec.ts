import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DashboardMissingPricesDialog from '@/modules/dashboard/DashboardMissingPricesDialog.vue';
import '@test/i18n';

const refreshPrice = vi.fn<(asset: string) => Promise<void>>().mockResolvedValue(undefined);

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: (): Record<string, unknown> => ({ refreshPrice }),
}));

function createWrapper(identifiers: string[]): VueWrapper<InstanceType<typeof DashboardMissingPricesDialog>> {
  return mount(DashboardMissingPricesDialog, {
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

describe('dashboardMissingPricesDialog', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    refreshPrice.mockClear();
  });

  it('should list a row per missing-price asset', () => {
    const wrapper = createWrapper(['ETH', 'BTC']);
    expect(wrapper.findAll('.asset')).toHaveLength(2);
    expect(wrapper.findAll('[data-testid=missing-price-add]')).toHaveLength(2);
    expect(wrapper.find('[data-testid=missing-prices-empty]').exists()).toBe(false);
  });

  it('should show the resolved state when nothing is left', () => {
    const wrapper = createWrapper([]);
    expect(wrapper.find('[data-testid=missing-prices-list]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=missing-prices-empty]').exists()).toBe(true);
  });

  it('should open a pre-filled add form for the picked asset and re-price it once saved', async () => {
    const wrapper = createWrapper(['ETH', 'BTC']);

    await wrapper.findAll('[data-testid=missing-price-add]')[0].trigger('click');

    const form = wrapper.findComponent({ name: 'LatestPriceFormDialog' });
    expect(form.exists()).toBe(true);
    expect(form.props('disableFromAsset')).toBe(true);
    expect(form.props('prefill')).toMatchObject({ fromAsset: 'ETH', price: '' });

    form.vm.$emit('refresh');
    await flushPromises();
    expect(refreshPrice).toHaveBeenCalledWith('ETH');
  });
});
