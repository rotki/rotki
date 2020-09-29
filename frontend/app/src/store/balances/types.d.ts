import { BigNumber } from 'bignumber.js';
import {
  BtcBalances,
  EthBalances,
  ManualBalanceWithValue,
  SupportedExchange
} from '@/services/balances/types';
import { Balance } from '@/services/types-api';
import { SupportedAsset } from '@/services/types-model';
import {
  AccountDataMap,
  Blockchain,
  ExchangeData,
  UsdToFiatExchangeRates
} from '@/typing/types';

export interface ManualBalancesByLocation {
  readonly location: string;
  readonly usdValue: BigNumber;
}

export interface ManualBalanceByLocation {
  [location: string]: BigNumber;
}

export interface AssetBalances {
  readonly [asset: string]: Balance;
}

export interface BalanceState {
  eth: EthBalances;
  btc: BtcBalances;
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

interface XpubPayload {
  readonly xpub: string;
  readonly derivationPath: string;
}

export interface BlockchainAccountPayload {
  readonly address: string;
  readonly blockchain: Blockchain;
  readonly label?: string;
  readonly tags: string[];
  readonly xpub?: XpubPayload;
}

export interface ExchangeBalancePayload {
  readonly name: string;
  readonly ignoreCache: boolean;
}

export interface BlockchainBalancePayload {
  readonly blockchain?: Blockchain;
  readonly ignoreCache: boolean;
}

export interface AllBalancePayload {
  readonly ignoreCache: boolean;
  readonly saveData: boolean;
}

export interface AccountBalance {
  readonly account: string;
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
}

export interface AssetBalance {
  readonly asset: string;
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
}
