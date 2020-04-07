import {
  AssetBalances,
  Balances,
  EthBalances,
  FiatBalance
} from '@/model/blockchain-balances';
import { DSRBalances, DSRHistory } from '@/services/types-model';
import {
  AccountDataMap,
  ExchangeData,
  UsdToFiatExchangeRates
} from '@/typing/types';
import { Zero } from '@/utils/bignumbers';

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
  dsrBalances: {
    currentDSR: Zero,
    balances: {}
  }
});

export const state: BalanceState = defaultState();
