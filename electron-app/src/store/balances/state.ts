import {
  AssetBalances,
  Balances,
  EthBalances,
  FiatBalance
} from '@/model/blockchain-balances';
import {
  AccountDataMap,
  ExchangeData,
  UsdToFiatExchangeRates
} from '@/typing/types';
import { DSRBalances, DSRHistory } from '@/services/types-model';

export interface BalanceState {
  eth: EthBalances;
  btc: Balances;
  totals: AssetBalances;
  usdToFiatExchangeRates: UsdToFiatExchangeRates;
  connectedExchanges: string[];
  exchangeBalances: ExchangeData;
  fiatBalances: FiatBalance[];
  ethAccounts: AccountDataMap;
  btcAccounts: AccountDataMap;
  dsrHistory: DSRHistory;
  dsrBalances: DSRBalances;
}

export const defaultState = (): BalanceState => ({
  eth: {},
  btc: {},
  totals: {},
  usdToFiatExchangeRates: {},
  connectedExchanges: [],
  exchangeBalances: {},
  fiatBalances: [],
  ethAccounts: {},
  btcAccounts: {},
  dsrHistory: {},
  dsrBalances: {}
});

export const state: BalanceState = defaultState();
