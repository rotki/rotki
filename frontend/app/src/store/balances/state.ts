import { BalanceState } from '@/store/balances/types';

export const defaultState = (): BalanceState => ({
  eth: {},
  eth2: {},
  ksm: {},
  dot: {},
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
  dotAccounts: [],
  avaxAccounts: [],
  btcAccounts: {
    standalone: [],
    xpubs: []
  },
  eth2Validators: [],
  supportedAssets: [],
  manualBalances: [],
  manualLiabilities: [],
  manualBalanceByLocation: {},
  prices: {},
  loopringBalances: {},
  nonFungibleBalances: {}
});

export const state: BalanceState = defaultState();
