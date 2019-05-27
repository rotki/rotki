import Vue from 'vue';
import Vuex, { StoreOptions } from 'vuex';
import { Currency } from '@/model/currency';
import { currencies } from '@/data/currencies';
import {
  AccountingSettings,
  AccountingSettingsUpdate,
  UsdToFiatExchangeRates,
  GeneralSettings,
  Balances
} from '@/typing/types';
import { defaultAccountingSettings, defaultSettings } from '@/data/factories';
import { BlockchainBalances } from '@/model/blockchain-balances';

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
    balances: {},
    nodeConnection: false,
    historyProcess: 0,
    blockchainBalances: {
      per_account: {},
      totals: {}
    },
    fiatTotal: 0,
    blockchainTotal: 0
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
    balances(state: RotkehlchenState, balances: Balances) {
      state.balances = balances;
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
    }
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
  balances: Balances;
  nodeConnection: boolean;
  historyProcess: number;
  blockchainBalances: BlockchainBalances;
  fiatTotal: number;
  blockchainTotal: number;
}
