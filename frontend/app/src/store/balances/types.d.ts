import {
  AssetBalances,
  Balances,
  EthBalances,
  ManualBalanceByLocation
} from '@/model/blockchain-balances';
import {
  ManualBalanceWithValue,
  SupportedExchange
} from '@/services/balances/types';
import { SupportedAsset } from '@/services/types-model';
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
  manualBalances: ManualBalanceWithValue[];
  manualBalanceByLocation: ManualBalanceByLocation;
}

export interface ExchangePayload {
  readonly exchange: string;
  readonly apiKey: string;
  readonly apiSecret: string;
  readonly passphrase: string | null;
}
