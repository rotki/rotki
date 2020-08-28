import { MutationTree } from 'vuex';
import { Balances, EthBalances } from '@/model/blockchain-balances';
import { AssetMovement, SupportedExchange } from '@/services/balances/types';
import { LimitedResponse } from '@/services/types-api';
import { ManualBalance, SupportedAsset } from '@/services/types-model';
import { defaultAssetMovements, defaultState } from '@/store/balances/state';
import { BalanceState } from '@/store/balances/types';
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
  ethAccounts(state: BalanceState, accounts: AccountDataMap) {
    state.ethAccounts = accounts;
  },
  btcAccounts(state: BalanceState, accounts: AccountDataMap) {
    state.btcAccounts = accounts;
  },
  supportedAssets(state: BalanceState, supportedAssets: SupportedAsset[]) {
    state.supportedAssets = supportedAssets;
  },
  manualBalances(state: BalanceState, manualBalances: ManualBalance[]) {
    state.manualBalances = manualBalances;
  },
  updateMovements(
    state: BalanceState,
    movements: LimitedResponse<AssetMovement[]>
  ) {
    state.assetMovements = {
      movements: [...state.assetMovements.movements, ...movements.entries],
      limit: movements.entriesLimit,
      found: movements.entriesFound
    };
  },
  resetMovements(state: BalanceState) {
    state.assetMovements = defaultAssetMovements();
  },
  reset(state: BalanceState) {
    Object.assign(state, defaultState());
  }
};
