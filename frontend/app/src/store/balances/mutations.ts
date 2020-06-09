import { MutationTree } from 'vuex';
import {
  Balances,
  EthBalances,
  FiatBalance
} from '@/model/blockchain-balances';
import {
  DSRBalances,
  DSRHistory,
  MakerDAOVault,
  MakerDAOVaultDetails,
  ManualBalance,
  SupportedAsset,
  Watcher
} from '@/services/types-model';
import { BalanceState, defaultState } from '@/store/balances/state';
import {
  AccountDataMap,
  ExchangeData,
  ExchangeInfo,
  UsdToFiatExchangeRates
} from '@/typing/types';

export const mutations: MutationTree<BalanceState> = {
  updateEth(state: BalanceState, payload: EthBalances) {
    state.eth = { ...payload };
  },
  updateBtc(state: BalanceState, payload: Balances) {
    state.btc = { ...payload };
  },
  updateTotals(state: BalanceState, payload: Balances) {
    state.totals = { ...payload };
  },
  usdToFiatExchangeRates(
    state: BalanceState,
    usdToFiatExchangeRates: UsdToFiatExchangeRates
  ) {
    state.usdToFiatExchangeRates = usdToFiatExchangeRates;
  },
  connectedExchanges(state: BalanceState, connectedExchanges: string[]) {
    state.connectedExchanges = connectedExchanges;
  },
  addExchange(state: BalanceState, exchangeName: string) {
    state.connectedExchanges.push(exchangeName);
  },
  removeExchange(state: BalanceState, exchangeName: string) {
    const exchanges = [...state.connectedExchanges];
    const balances = { ...state.exchangeBalances };
    const index = exchanges.findIndex(value => value === exchangeName);
    // can't modify in place or else the vue reactivity does not work
    exchanges.splice(index, 1);
    delete balances[exchangeName];
    state.connectedExchanges = exchanges;
    state.exchangeBalances = balances;
  },
  addExchangeBalances(state: BalanceState, data: ExchangeInfo) {
    const update: ExchangeData = {};
    update[data.name] = data.balances;
    state.exchangeBalances = { ...state.exchangeBalances, ...update };
  },
  fiatBalances(state: BalanceState, fiatBalances: FiatBalance[]) {
    state.fiatBalances = [...fiatBalances];
  },
  ethAccounts(state: BalanceState, accounts: AccountDataMap) {
    state.ethAccounts = accounts;
  },
  btcAccounts(state: BalanceState, accounts: AccountDataMap) {
    state.btcAccounts = accounts;
  },
  dsrHistory(state: BalanceState, history: DSRHistory) {
    state.dsrHistory = history;
  },
  dsrBalances(state: BalanceState, balances: DSRBalances) {
    state.dsrBalances = balances;
  },
  supportedAssets(state: BalanceState, supportedAssets: SupportedAsset[]) {
    state.supportedAssets = supportedAssets;
  },
  manualBalances(state: BalanceState, manualBalances: ManualBalance[]) {
    state.manualBalances = manualBalances;
  },
  watchers(state: BalanceState, watchers: Watcher[]) {
    state.watchers = watchers;
  },
  makerDAOVaults(state: BalanceState, makerDAOVaults: MakerDAOVault[]) {
    state.makerDAOVaults = makerDAOVaults;
  },
  makerDAOVaultDetails(
    state: BalanceState,
    makerDAOVaultDetails: MakerDAOVaultDetails[]
  ) {
    state.makerDAOVaultDetails = makerDAOVaultDetails;
  },
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  reset(state: BalanceState) {
    state = Object.assign(state, defaultState());
  }
};
