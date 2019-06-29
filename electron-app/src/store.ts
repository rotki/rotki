import Vue from 'vue';
import Vuex, { StoreOptions } from 'vuex';
import { Currency } from '@/model/currency';
import { currencies } from '@/data/currencies';
import {
  AccountingSettings,
  AccountingSettingsUpdate,
  UsdToFiatExchangeRates,
  GeneralSettings,
  ExchangeInfo,
  ExchangeData
} from '@/typing/types';
import { defaultAccountingSettings, defaultSettings } from '@/data/factories';
import {
  BlockchainBalances,
  ApiBalances,
  EthBalances,
  AccountBalance
} from '@/model/blockchain-balances';
import { assetSum } from '@/utils/calculation';
import { notifications } from '@/notifications';

Vue.use(Vuex);

let store: StoreOptions<RotkehlchenState> = {
  state: {
    newUser: false,
    currency: currencies[0],
    userLogged: false,
    settings: defaultSettings(),
    accountingSettings: defaultAccountingSettings(),
    logout: false,
    premium: false,
    premiumSync: false,
    usdToFiatExchangeRates: {},
    nodeConnection: false,
    historyProcess: 0,
    blockchainBalances: {
      per_account: {},
      totals: {}
    },
    fiatTotal: 0,
    blockchainTotal: 0,
    connectedExchanges: [],
    exchangeBalances: {},
    ethBalances: {},
    btcBalances: {}
  },
  mutations: {
    defaultCurrency(state: RotkehlchenState, currency: Currency) {
      state.currency = currency;
    },
    logged(state: RotkehlchenState, logged: boolean) {
      state.userLogged = logged;
    },
    logout(state: RotkehlchenState, logout: boolean) {
      state.logout = logout;
    },
    settings(state: RotkehlchenState, settings: GeneralSettings) {
      state.settings = Object.assign({}, settings);
    },
    premium(state: RotkehlchenState, premium: boolean) {
      state.premium = premium;
    },
    premiumSync(state: RotkehlchenState, premiumSync: boolean) {
      state.premiumSync = premiumSync;
    },
    accountingSettings(
      state: RotkehlchenState,
      accountingSettings: AccountingSettings
    ) {
      state.accountingSettings = Object.assign({}, accountingSettings);
    },
    updateAccountingSetting(
      state: RotkehlchenState,
      setting: AccountingSettingsUpdate
    ) {
      state.accountingSettings = Object.assign(
        {},
        state.accountingSettings,
        setting
      );
    },
    newUser(state: RotkehlchenState, newUser: boolean) {
      state.newUser = newUser;
    },
    usdToFiatExchangeRates(
      state: RotkehlchenState,
      usdToFiatExchangeRates: UsdToFiatExchangeRates
    ) {
      state.usdToFiatExchangeRates = usdToFiatExchangeRates;
    },
    nodeConnection(state: RotkehlchenState, nodeConnection: boolean) {
      state.nodeConnection = nodeConnection;
    },
    historyProcess(state: RotkehlchenState, historyProcess: number) {
      state.historyProcess = historyProcess;
    },
    blockchainBalances(
      state: RotkehlchenState,
      blockchainBalances: BlockchainBalances
    ) {
      state.blockchainBalances = blockchainBalances;
    },
    fiatTotal(state: RotkehlchenState, fiatTotal: number) {
      state.fiatTotal = fiatTotal;
    },
    blockchainTotal(state: RotkehlchenState, blockchainTotal: number) {
      state.blockchainTotal = blockchainTotal;
    },
    connectedExchanges(state: RotkehlchenState, connectedExchanges: string[]) {
      state.connectedExchanges = connectedExchanges;
    },
    addExchange(state: RotkehlchenState, exchangeName: string) {
      state.connectedExchanges.push(exchangeName);
    },
    removeExchange(state: RotkehlchenState, exchangeName: string) {
      const index = state.connectedExchanges.findIndex(
        value => value === exchangeName
      );
      state.connectedExchanges.splice(index, 1);
    },
    addExchangeBalances(state: RotkehlchenState, data: ExchangeInfo) {
      const update: ExchangeData = {};
      update[data.name] = data.balances;
      state.exchangeBalances = Object.assign(
        {},
        state.exchangeBalances,
        update
      );
    },
    addPerAccountBtc(state: RotkehlchenState, data: ApiBalances) {
      state.btcBalances = Object.assign({}, data);
    },
    addPerAccountEth(state: RotkehlchenState, data: EthBalances) {
      state.ethBalances = Object.assign({}, data);
    }
  },
  actions: {},
  getters: {
    blockchainTotals: (state: RotkehlchenState) => {
      return Object.values(state.blockchainBalances.totals);
    },
    floatingPrecision: (state: RotkehlchenState) => {
      return state.settings.floatingPrecision;
    },
    dateDisplayFormat: (state: RotkehlchenState) => {
      return state.settings.dateDisplayFormat;
    },
    exchanges: (state: RotkehlchenState) => {
      const balances = state.exchangeBalances;
      return Object.keys(balances).map(value => ({
        name: value,
        balances: balances[value],
        totals: assetSum(balances[value])
      }));
    },
    perAccountEth: (state: RotkehlchenState) => {
      let balances = state.ethBalances;
      return Object.keys(balances).map(
        value =>
          ({
            account: value,
            amount: balances[value].eth,
            usdValue: balances[value].usdValue
          } as AccountBalance)
      );
    }
  },
  modules: {
    notifications
  }
};
export default new Vuex.Store(store);

export interface RotkehlchenState {
  newUser: boolean;
  currency: Currency;
  userLogged: boolean;
  settings: GeneralSettings;
  accountingSettings: AccountingSettings;
  logout: boolean;
  premium: boolean;
  premiumSync: boolean;
  usdToFiatExchangeRates: UsdToFiatExchangeRates;
  nodeConnection: boolean;
  historyProcess: number;
  blockchainBalances: BlockchainBalances;
  fiatTotal: number;
  blockchainTotal: number;
  connectedExchanges: string[];
  exchangeBalances: ExchangeData;
  ethBalances: EthBalances;
  btcBalances: ApiBalances;
}
