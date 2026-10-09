import type { useExchangeBalancesPage } from '@/pages/balances/exchange/use-exchange-balances-page';
import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import ExchangeBalancesPage from '@/pages/balances/exchange/[[exchange]].vue';

const navigateToExchangeSetup = vi.fn();
const refreshExchangeBalances = vi.fn(async (): Promise<void> => {});
const refreshInView = vi.fn(async (): Promise<void> => {});
const refreshSelectedExchangeBalances = vi.fn(async (): Promise<void> => {});

interface PageState {
  balances: AssetBalanceWithPrice[];
  loading: boolean;
  used: string[];
  view: 'balances' | 'savings';
}

const pageState = vi.hoisted((): PageState => ({
  balances: [],
  loading: false,
  used: [],
  view: 'balances',
}));

const RefreshButtonStub = defineComponent({
  emits: ['refresh', 'refresh-all', 'refresh-exchange'],
  name: 'ExchangeBalancesRefreshButtonStub',
  props: {
    exchanges: { default: () => [], type: Array },
    loading: { default: false, type: Boolean },
    selected: { default: undefined, type: String },
  },
  template: '<div data-testid="refresh-button" />',
});

const CardsStub = defineComponent({
  name: 'ExchangeBalanceCardsStub',
  props: {
    exchangeBalance: { default: undefined, type: Function },
    exchanges: { default: () => [], type: Array },
    selected: { default: undefined, type: String },
    total: { default: undefined, type: Object },
  },
  template: '<div data-testid="exchange-cards" />',
});

const EmptyStub = defineComponent({
  emits: ['connect'],
  name: 'ExchangeBalancesEmptyStub',
  template: '<div data-testid="exchanges-empty" />',
});

const AssetBalancesStub = defineComponent({
  name: 'AssetBalancesStub',
  props: {
    balances: { default: () => [], type: Array },
    breakdown: { default: undefined, type: Object },
    loading: { default: false, type: Boolean },
    search: { default: '', type: String },
    showPerProtocol: { default: false, type: Boolean },
    stickyHeader: { default: false, type: Boolean },
  },
  template: '<div data-testid="asset-balances" />',
});

vi.mock('@/pages/balances/exchange/use-exchange-balances-page', async () => {
  const { computed, shallowRef } = await import('vue');
  return {
    isBinance: (id?: string): boolean => id === 'binance',
    useExchangeBalancesPage: (): ReturnType<typeof useExchangeBalancesPage> => ({
      balances: computed(() => pageState.balances),
      exchangeBalance: () => bigNumberify(100),
      isExchangeLoading: computed(() => pageState.loading),
      modelView: shallowRef(pageState.view),
      navigateToExchangeSetup,
      refreshExchangeBalances,
      refreshInView,
      refreshSelectedExchangeBalances,
      sortedExchanges: computed(() => pageState.used),
      totalBalance: computed(() => bigNumberify(200)),
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
          AssetBalances: AssetBalancesStub,
          BinanceSavingDetail: { props: ['exchange'], template: '<div data-testid="binance-savings" />' },
          ExchangeBalanceCards: CardsStub,
          ExchangeBalancesEmpty: EmptyStub,
          ExchangeBalancesRefreshButton: RefreshButtonStub,
          HideSmallBalances: { props: ['source'], template: '<div />' },
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
    pageState.loading = false;
    pageState.used = [];
    pageState.view = 'balances';
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe('with no exchange connected', () => {
    it('should show the empty state instead of the cards and table', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(EmptyStub).exists()).toBe(true);
      expect(wrapper.findComponent(CardsStub).exists()).toBe(false);
      expect(wrapper.findComponent(AssetBalancesStub).exists()).toBe(false);
    });

    it('should open the add dialog on the exchange the empty state picks', () => {
      wrapper = mountPage();

      wrapper.findComponent(EmptyStub).vm.$emit('connect', 'kraken');

      expect(navigateToExchangeSetup).toHaveBeenCalledWith('kraken');
    });

    it('should still offer the header add button', async () => {
      wrapper = mountPage();

      await wrapper.find('[data-testid=add-exchange]').trigger('click');

      expect(navigateToExchangeSetup).toHaveBeenCalledTimes(1);
    });
  });

  describe('with exchanges connected', () => {
    beforeEach(() => {
      pageState.used = ['kraken', 'binance'];
    });

    it('should show a card per exchange, with none selected on the all view', () => {
      wrapper = mountPage();

      const cards = wrapper.findComponent(CardsStub);
      expect(cards.props('exchanges')).toEqual(['kraken', 'binance']);
      expect(cards.props('selected')).toBeUndefined();
    });

    it('should list every exchange balances with their locations on the all view', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(AssetBalancesStub).props('showPerProtocol')).toBe(true);
    });

    it('should show the exchange in the route without a location column', () => {
      pageState.balances = [{
        amount: bigNumberify(1),
        asset: 'ETH',
        price: bigNumberify(2),
        value: bigNumberify(2),
      }];

      wrapper = mountPage('kraken');

      const table = wrapper.findComponent(AssetBalancesStub);
      expect(wrapper.findComponent(CardsStub).props('selected')).toBe('kraken');
      expect(table.props('balances')).toHaveLength(1);
      expect(table.props('showPerProtocol')).toBe(false);
    });

    it('should wire the refresh button to the page, every exchange and a single one', () => {
      wrapper = mountPage('kraken');

      const button = wrapper.findComponent(RefreshButtonStub);
      expect(button.props('selected')).toBe('kraken');

      button.vm.$emit('refresh');
      button.vm.$emit('refresh-all');
      button.vm.$emit('refresh-exchange', 'binance');

      expect(refreshInView).toHaveBeenCalledOnce();
      expect(refreshExchangeBalances).toHaveBeenCalledOnce();
      expect(refreshSelectedExchangeBalances).toHaveBeenCalledWith('binance');
    });

    it('should offer the savings view only for binance', () => {
      wrapper = mountPage('kraken');
      expect(wrapper.find('[data-testid=exchange-balances-view]').exists()).toBe(false);
      wrapper.unmount();

      wrapper = mountPage('binance');
      expect(wrapper.find('[data-testid=exchange-balances-view]').exists()).toBe(true);
    });

    it('should show the savings history in place of the table when chosen', () => {
      pageState.view = 'savings';

      wrapper = mountPage('binance');

      expect(wrapper.find('[data-testid=binance-savings]').exists()).toBe(true);
      expect(wrapper.findComponent(AssetBalancesStub).exists()).toBe(false);
    });
  });
});
