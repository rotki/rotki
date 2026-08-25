import type { useExchangeBalancesPage } from '@/pages/balances/exchange/use-exchange-balances-page';
import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import ExchangeBalancesPage from '@/pages/balances/exchange/[[exchange]].vue';

const navigateToExchangeSetup = vi.fn();
const openExchangeDetails = vi.fn();
const refreshExchangeBalances = vi.fn(async (): Promise<void> => {});
const refreshSelectedExchangeBalances = vi.fn(async (): Promise<void> => {});

interface PageState {
  balances: AssetBalanceWithPrice[];
  detailTab: number;
  loading: boolean;
  used: string[];
}

const pageState = vi.hoisted((): PageState => ({
  balances: [],
  detailTab: 0,
  loading: false,
  used: [],
}));

const DetailPanelStub = defineComponent({
  emits: ['refresh', 'update:modelValue'],
  name: 'ExchangeDetailPanelStub',
  props: {
    balances: { default: () => [], type: Array },
    exchange: { default: '', type: String },
    loading: { default: false, type: Boolean },
    modelValue: { default: 0, type: Number },
  },
  template: '<div data-testid="detail-panel" />',
});

vi.mock('@/pages/balances/exchange/use-exchange-balances-page', async () => {
  const { computed, shallowRef } = await import('vue');
  return {
    isBinance: (id?: string): boolean => id === 'binance',
    useExchangeBalancesPage: (): ReturnType<typeof useExchangeBalancesPage> => ({
      balances: computed(() => pageState.balances),
      exchangeBalance: () => bigNumberify(100),
      isExchangeLoading: computed(() => pageState.loading),
      modelExchangeDetailTabs: shallowRef(pageState.detailTab),
      modelSelectedExchange: shallowRef(''),
      modelSelectedTab: shallowRef(undefined),
      navigateToExchangeSetup,
      openExchangeDetails,
      refreshExchangeBalances,
      refreshSelectedExchangeBalances,
      sortedExchanges: computed(() => pageState.used),
      usedExchanges: computed(() => pageState.used),
    }),
  };
});

describe('pages/balances/exchange/[[exchange]]', () => {
  let wrapper: VueWrapper<InstanceType<typeof ExchangeBalancesPage>>;

  function mountPage(exchange?: string): VueWrapper<InstanceType<typeof ExchangeBalancesPage>> {
    return mount(ExchangeBalancesPage, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          ExchangeAmountRow: { props: ['balance', 'exchange'], template: '<div />' },
          ExchangeDetailPanel: DetailPanelStub,
          FiatDisplay: { props: ['value'], template: '<div />' },
          HideSmallBalances: { props: ['source'], template: '<div />' },
          InternalLink: { props: ['to'], template: '<a><slot /></a>' },
          LocationDisplay: { props: ['identifier', 'openDetails', 'size'], template: '<div data-testid="exchange-tab" />' },
          RuiMenuSelect: { props: ['modelValue', 'options', 'label'], template: '<div data-testid="exchange-picker" />' },
          TablePageLayout: { props: ['title'], template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
      props: { exchange },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    pageState.balances = [];
    pageState.detailTab = 0;
    pageState.loading = false;
    pageState.used = [];
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe('with no exchange connected', () => {
    it('should offer the setup shortcut instead of the picker', async () => {
      wrapper = mountPage();

      expect(wrapper.find('[data-testid=exchange-picker]').exists()).toBe(false);
      await wrapper.find('[data-testid=add-exchange]').trigger('click');

      expect(navigateToExchangeSetup).toHaveBeenCalledTimes(1);
    });
  });

  describe('with exchanges connected', () => {
    beforeEach(() => {
      pageState.used = ['kraken', 'binance'];
    });

    it('should show a tab per exchange', () => {
      wrapper = mountPage();

      expect(wrapper.findAll('[data-testid=exchange-tab]')).toHaveLength(2);
    });

    it('should show the hint rather than a panel until one is chosen', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(DetailPanelStub).exists()).toBe(false);
      expect(wrapper.text()).toContain('exchange_balances.select_hint');
    });

    it('should show the panel for the exchange in the route, with its balances', () => {
      pageState.balances = [{
        amount: bigNumberify(1),
        asset: 'ETH',
        price: bigNumberify(2),
        value: bigNumberify(2),
      }];

      wrapper = mountPage('kraken');

      const panel = wrapper.findComponent(DetailPanelStub);
      expect(panel.exists()).toBe(true);
      expect(panel.props('exchange')).toBe('kraken');
      expect(panel.props('balances')).toHaveLength(1);
    });

    it('should refresh a single exchange from the panel', () => {
      wrapper = mountPage('kraken');

      wrapper.findComponent(DetailPanelStub).vm.$emit('refresh', 'kraken');

      expect(refreshSelectedExchangeBalances).toHaveBeenCalledWith('kraken');
    });

    it('should refresh every exchange from the toolbar button', async () => {
      wrapper = mountPage('kraken');

      await wrapper.find('[data-testid=refresh-exchange-balances]').trigger('click');

      expect(refreshExchangeBalances).toHaveBeenCalledTimes(1);
    });

    it('should block the toolbar refresh while a detail tab other than the first is open', () => {
      pageState.detailTab = 1;

      wrapper = mountPage('kraken');

      expect(wrapper.find('[data-testid=refresh-exchange-balances]').attributes('disabled')).toBeDefined();
    });
  });
});
