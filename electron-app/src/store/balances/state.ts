import {
  Balances,
  EthBalances,
  FiatBalance
} from '@/model/blockchain-balances';
import { ExchangeData, UsdToFiatExchangeRates } from '@/typing/types';

export const state: BalanceState = {
  eth: {},
  btc: {},
  totals: {},
  usdToFiatExchangeRates: {},
  connectedExchanges: [],
  exchangeBalances: {},
  fiatBalances: []
};

export interface BalanceState {
  eth: EthBalances;
  btc: Balances;
  totals: Balances;
  usdToFiatExchangeRates: UsdToFiatExchangeRates;
  connectedExchanges: string[];
  exchangeBalances: ExchangeData;
  fiatBalances: FiatBalance[];
}
