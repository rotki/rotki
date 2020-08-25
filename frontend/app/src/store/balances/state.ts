import {
  AssetBalances,
  Balances,
  EthBalances,
  ManualBalanceByLocation
} from '@/model/blockchain-balances';
import { SupportedExchange } from '@/services/balances/types';
import { ManualBalance, SupportedAsset } from '@/services/types-model';
import {
  AccountDataMap,
  ExchangeData,
  UsdToFiatExchangeRates
} from '@/typing/types';

export interface BalanceState {
  eth: EthBalances;
  btc: Balances;
  totals: AssetBalances;
  usdToFiatExchangeRates: UsdToFiatExchangeRates;
  connectedExchanges: SupportedExchange[];
  exchangeBalances: ExchangeData;
  ethAccounts: AccountDataMap;
  btcAccounts: AccountDataMap;
  supportedAssets: SupportedAsset[];
  manualBalances: ManualBalance[];
  manualBalanceByLocation: ManualBalanceByLocation;
}

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
  manualBalanceByLocation: {}
});

export const state: BalanceState = defaultState();
