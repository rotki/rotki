import {
  AssetBalances,
  Balances,
  EthBalances,
  FiatBalance
} from '@/model/blockchain-balances';
import { ExchangeData, UsdToFiatExchangeRates } from '@/typing/types';

export interface BalanceState {
  eth: EthBalances;
  btc: Balances;
  totals: AssetBalances;
  usdToFiatExchangeRates: UsdToFiatExchangeRates;
  connectedExchanges: string[];
  exchangeBalances: ExchangeData;
  fiatBalances: FiatBalance[];
}

export const defaultState = (): BalanceState => ({
  eth: {},
  btc: {},
  totals: {},
  usdToFiatExchangeRates: {},
  connectedExchanges: [],
  exchangeBalances: {},
  fiatBalances: []
});

export const state: BalanceState = defaultState();
