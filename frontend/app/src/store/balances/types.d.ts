import {
  AssetBalances,
  Balances,
  EthBalances,
  ManualBalanceByLocation
} from '@/model/blockchain-balances';
import { AssetMovement, SupportedExchange } from '@/services/balances/types';
import { ManualBalance, SupportedAsset } from '@/services/types-model';
import {
  AccountDataMap,
  ExchangeData,
  UsdToFiatExchangeRates
} from '@/typing/types';

export interface AssetMovements {
  readonly limit: number;
  readonly found: number;
  readonly movements: AssetMovement[];
}

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
  assetMovements: AssetMovements;
}
