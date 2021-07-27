import { BalanceState } from '@/store/balances/types';

export const defaultState = (): BalanceState => ({
  eth: {},
  ksm: {},
  avax: {},
  btc: {
    standalone: {},
    xpubs: []
  },
  totals: {},
  liabilities: {},
  usdToFiatExchangeRates: {},
  connectedExchanges: [],
  exchangeBalances: {},
  ethAccounts: [],
  ksmAccounts: [],
  avaxAccounts: [],
  btcAccounts: {
    standalone: [],
    xpubs: []
  },
  supportedAssets: [],
  manualBalances: [],
  manualBalanceByLocation: {},
  prices: {},
  loopringBalances: {}
});

export const state: BalanceState = defaultState();
