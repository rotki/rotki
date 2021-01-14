import { MutationTree } from 'vuex';
import {
  Balances,
  BtcBalances,
  BlockchainAssetBalances,
  ManualBalanceWithValue,
  SupportedExchange
} from '@/services/balances/types';
import { BtcAccountData, GeneralAccountData } from '@/services/types-api';
import { SupportedAsset } from '@/services/types-model';
import { defaultState } from '@/store/balances/state';
import { BalanceState } from '@/store/balances/types';
import { ExchangeData, ExchangeInfo, ExchangeRates } from '@/typing/types';

export const mutations: MutationTree<BalanceState> = {
  updateEth(state: BalanceState, payload: BlockchainAssetBalances) {
    state.eth = { ...payload };
  },
  updateBtc(state: BalanceState, payload: BtcBalances) {
    state.btc = { ...payload };
  },
  updateKsm(state: BalanceState, payload: BlockchainAssetBalances) {
    state.ksm = { ...payload };
  },
  updateTotals(state: BalanceState, payload: Balances) {
    state.totals = { ...state.totals, ...payload };
  },
  updateLiabilities(state: BalanceState, payload: Balances) {
    state.liabilities = { ...state.liabilities, ...payload };
  },
  usdToFiatExchangeRates(
    state: BalanceState,
    usdToFiatExchangeRates: ExchangeRates
  ) {
    state.usdToFiatExchangeRates = usdToFiatExchangeRates;
  },
  connectedExchanges(
    state: BalanceState,
    connectedExchanges: SupportedExchange[]
  ) {
    state.connectedExchanges = connectedExchanges;
  },
  addExchange(state: BalanceState, exchangeName: SupportedExchange) {
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
  ethAccounts(state: BalanceState, accounts: GeneralAccountData[]) {
    state.ethAccounts = accounts;
  },
  btcAccounts(state: BalanceState, accounts: BtcAccountData) {
    state.btcAccounts = accounts;
  },
  ksmAccounts(state: BalanceState, accounts: GeneralAccountData[]) {
    state.ksmAccounts = accounts;
  },
  supportedAssets(state: BalanceState, supportedAssets: SupportedAsset[]) {
    state.supportedAssets = supportedAssets;
  },
  manualBalances(
    state: BalanceState,
    manualBalances: ManualBalanceWithValue[]
  ) {
    state.manualBalances = manualBalances;
  },
  reset(state: BalanceState) {
    Object.assign(state, defaultState());
  }
};
