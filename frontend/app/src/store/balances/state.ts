import { AssetMovements, BalanceState } from '@/store/balances/types';

export const defaultAssetMovements = (): AssetMovements => ({
  found: 0,
  limit: 0,
  movements: []
});

export const defaultState = (): BalanceState => ({
  eth: {},
  btc: {},
  totals: {},
  usdToFiatExchangeRates: {},
  connectedExchanges: [],
  exchangeBalances: {},
  ethAccounts: {},
  btcAccounts: {},
  supportedAssets: [],
  manualBalances: [],
  manualBalanceByLocation: {},
  assetMovements: defaultAssetMovements()
});

export const state: BalanceState = defaultState();
