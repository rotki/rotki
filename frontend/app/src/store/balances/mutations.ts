import { MutationTree } from 'vuex';
import { Exchange } from '@/model/action-result';
import { SupportedAsset } from '@/services/assets/types';
import {
  Balances,
  BtcBalances,
  BlockchainAssetBalances,
  ManualBalanceWithValue
} from '@/services/balances/types';
import { BtcAccountData, GeneralAccountData } from '@/services/types-api';
import {
  MUTATION_UPDATE_LOOPRING_BALANCES,
  MUTATION_UPDATE_PRICES
} from '@/store/balances/mutation-types';
import { defaultState } from '@/store/balances/state';
import {
  AccountAssetBalances,
  AssetPrices,
  BalanceState,
  EditExchange
} from '@/store/balances/types';
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
  connectedExchanges(state: BalanceState, connectedExchanges: Exchange[]) {
    state.connectedExchanges = connectedExchanges;
  },
  addExchange(state: BalanceState, exchange: Exchange) {
    state.connectedExchanges.push(exchange);
  },
  editExchange(
    state: BalanceState,
    {
      exchange: { location, name: oldName, krakenAccountType, ftxSubaccount },
      newName
    }: EditExchange
  ) {
    const exchanges = [...state.connectedExchanges];
    const name = newName ?? oldName;
    const index = exchanges.findIndex(
      value => value.name === oldName && value.location === location
    );
    exchanges[index] = Object.assign(exchanges[index], {
      name,
      location,
      krakenAccountType,
      ftxSubaccount
    });
    state.connectedExchanges = exchanges;
  },
  removeExchange(state: BalanceState, exchange: Exchange) {
    const exchanges = [...state.connectedExchanges];
    const balances = { ...state.exchangeBalances };
    const index = exchanges.findIndex(
      ({ location, name }) =>
        name === exchange.name && location === exchange.location
    );
    // can't modify in place or else the vue reactivity does not work
    exchanges.splice(index, 1);
    delete balances[exchange.location];
    state.connectedExchanges = exchanges;
    state.exchangeBalances = balances;
  },
  updateExchangeBalances(state: BalanceState, data: ExchangeData) {
    state.exchangeBalances = data;
  },
  addExchangeBalances(state: BalanceState, data: ExchangeInfo) {
    const update: ExchangeData = {};
    update[data.location] = data.balances;
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
  [MUTATION_UPDATE_PRICES](state: BalanceState, prices: AssetPrices) {
    state.prices = prices;
  },
  [MUTATION_UPDATE_LOOPRING_BALANCES](
    state: BalanceState,
    balances: AccountAssetBalances
  ) {
    state.loopringBalances = balances;
  },
  reset(state: BalanceState) {
    Object.assign(state, defaultState());
  }
};
