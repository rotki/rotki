import {
  AssetBalances,
  Balances,
  EthBalances,
  ManualBalanceByLocation,
  FiatBalance
} from '@/model/blockchain-balances';
import {
  DSRBalances,
  DSRHistory,
  MakerDAOVault,
  ManualBalance,
  SupportedAsset
} from '@/services/types-model';
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
  supportedAssets: SupportedAsset[];
  manualBalances: ManualBalance[];
  manualBalanceByLocation: ManualBalanceByLocation;
  makerDAOVaults: MakerDAOVault[];
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
  },
  supportedAssets: [],
  manualBalances: [],
  manualBalanceByLocation: {},
  makerDAOVaults: []
});

export const state: BalanceState = defaultState();
