import type { ExchangeAccountOption, useExchangeAccountSelection } from '@/modules/balances/exchanges/use-exchange-account-selection';
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
  failed: boolean;
  loading: boolean;
  used: string[];
  view: 'balances' | 'savings';
}

const pageState = vi.hoisted((): PageState => ({
  balances: [],
  failed: false,
  loading: false,
  used: [],
  view: 'balances',
}));

const selectionState = vi.hoisted((): { account?: string; accountBalances?: AssetBalanceWithPrice[]; accounts: ExchangeAccountOption[] } => ({
  accounts: [],
}));

const PickerStub = defineComponent({
  name: 'ExchangeAccountPickerStub',
  props: {
    accounts: { default: () => [], type: Array },
    modelValue: { default: undefined, type: String },
    total: { default: undefined, type: Object },
  },
  template: '<div data-testid="account-picker" />',
});

vi.mock('@/modules/balances/exchanges/use-exchange-account-selection', async () => {
  const { computed, shallowRef } = await import('vue');
  return {
    useExchangeAccountSelection: (): ReturnType<typeof useExchangeAccountSelection> => {
      const account = shallowRef<string | undefined>(selectionState.account);
      return {
        accountBalances: computed(() => selectionState.accountBalances),
        accounts: computed(() => selectionState.accounts),
        modelAccount: computed<string | undefined>({ get: () => account.value, set: (value) => { account.value = value; } }),
        picked: computed(() => selectionState.accounts.find(option => option.identifier === account.value)),
      };
    },
  };
});

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
    display: { default: undefined, type: Object },
  },
  template: '<div data-testid="asset-balances"><slot name="empty" /></div>',
});

vi.mock('@/pages/balances/exchange/use-exchange-balances-page', async () => {
  const { computed, shallowRef } = await import('vue');
  return {
    isBinance: (id?: string): boolean => id === 'binance',
    useExchangeBalancesPage: (): ReturnType<typeof useExchangeBalancesPage> => ({
      balances: computed(() => pageState.balances),
      exchangeBalance: () => bigNumberify(100),
      isExchangeLoading: computed(() => pageState.loading),
      lastRefreshFailed: computed(() => pageState.failed),
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
          ExchangeAccountPicker: PickerStub,
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
    pageState.failed = false;
    pageState.loading = false;
    pageState.used = [];
    pageState.view = 'balances';
    selectionState.account = undefined;
    selectionState.accountBalances = undefined;
    selectionState.accounts = [];
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

    it('should say an empty table follows a failed refresh, not an empty exchange', () => {
      pageState.failed = true;
      wrapper = mountPage('kraken');

      expect(wrapper.find('[data-testid=exchange-balances-refresh-failed]').exists()).toBe(true);
    });

    it('should keep the plain empty table after a refresh that worked', () => {
      wrapper = mountPage('kraken');

      expect(wrapper.find('[data-testid=exchange-balances-refresh-failed]').exists()).toBe(false);
    });

    it('should list every exchange balances with their locations on the all view', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(AssetBalancesStub).props('display')).toMatchObject({ showPerProtocol: true });
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
      expect(table.props('display')).toMatchObject({ showPerProtocol: false });
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

  describe('account picker', () => {
    beforeEach(() => {
      pageState.used = ['kraken', 'binance'];
    });

    const accounts: ExchangeAccountOption[] = [
      { identifier: 'kraken-Main', loaded: true, name: 'Main', share: '66.67', value: bigNumberify(10) },
      { error: 'Invalid key', identifier: 'kraken-Bot', loaded: false, name: 'Bot', share: '0.00', value: bigNumberify(0) },
    ];

    it('should hide the picker when the exchange has nothing to pick between', () => {
      wrapper = mountPage('kraken');

      expect(wrapper.findComponent(PickerStub).exists()).toBe(false);
    });

    it('should offer the picker for an exchange with several connections', () => {
      selectionState.accounts = accounts;
      wrapper = mountPage('kraken');

      expect(wrapper.findComponent(PickerStub).props('accounts')).toEqual(accounts);
    });

    it('should hide the picker on the binance savings view', () => {
      selectionState.accounts = accounts;
      pageState.view = 'savings';
      wrapper = mountPage('binance');

      expect(wrapper.findComponent(PickerStub).exists()).toBe(false);
    });

    it('should feed the table the picked account balances instead of the exchange total', () => {
      pageState.balances = [{ amount: bigNumberify(1), asset: 'ETH', price: bigNumberify(2), value: bigNumberify(2) }];
      selectionState.accounts = accounts;
      selectionState.accountBalances = [{ amount: bigNumberify(3), asset: 'SOL', price: bigNumberify(1), value: bigNumberify(3) }];
      wrapper = mountPage('kraken');

      expect(wrapper.findComponent(AssetBalancesStub).props('balances')).toEqual(selectionState.accountBalances);
    });

    it('should hand the picker the exchange total its card shows', () => {
      selectionState.accounts = accounts;
      wrapper = mountPage('kraken');

      expect(wrapper.findComponent(PickerStub).props('total')).toEqual(bigNumberify(100));
    });

    it.each([
      { case: 'that refreshed fine is empty, though another account failed', failed: false, options: accounts, picked: 'kraken-Main' },
      { case: 'whose refresh failed is unknown', failed: true, options: accounts, picked: 'kraken-Bot' },
      { case: 'no refresh has loaded is unknown, with no error of its own', failed: true, options: [accounts[0], { ...accounts[1], error: undefined }], picked: 'kraken-Bot' },
    ])('should say a picked account $case', ({ failed, options, picked }) => {
      pageState.failed = true;
      selectionState.accounts = options;
      selectionState.account = picked;
      selectionState.accountBalances = [];
      wrapper = mountPage('kraken');

      expect(wrapper.find('[data-testid=exchange-balances-refresh-failed]').exists()).toBe(failed);
    });
  });
});
