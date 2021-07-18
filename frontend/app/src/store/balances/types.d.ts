import { BigNumber } from 'bignumber.js';
import { Exchange, PriceOracles } from '@/model/action-result';
import { SupportedAsset } from '@/services/assets/types';
import {
  BlockchainAssetBalances,
  BtcBalances,
  ManualBalanceWithValue,
  SupportedExchange
} from '@/services/balances/types';
import { SupportedModules } from '@/services/session/types';
import {
  Balance,
  BtcAccountData,
  GeneralAccountData,
  HasBalance
} from '@/services/types-api';
import { KRAKEN_ACCOUNT_TYPES } from '@/store/balances/const';
import { Section } from '@/store/const';
import { Nullable } from '@/types';
import {
  Blockchain,
  ExchangeData,
  ExchangeRates,
  GeneralAccount,
  SupportedL2Protocol
} from '@/typing/types';

export interface LocationBalance {
  readonly location: string;
  readonly usdValue: BigNumber;
}

export interface BalanceByLocation {
  [location: string]: BigNumber;
}

export interface AssetBalances {
  readonly [asset: string]: Balance;
}

export interface AccountAssetBalances {
  readonly [account: string]: AssetBalances;
}

export interface BalanceState {
  loopringBalances: AccountAssetBalances;
  eth: BlockchainAssetBalances;
  btc: BtcBalances;
  ksm: BlockchainAssetBalances;
  totals: AssetBalances;
  liabilities: AssetBalances;
  usdToFiatExchangeRates: ExchangeRates;
  connectedExchanges: Exchange[];
  exchangeBalances: ExchangeData;
  ethAccounts: GeneralAccountData[];
  btcAccounts: BtcAccountData;
  ksmAccounts: GeneralAccountData[];
  supportedAssets: SupportedAsset[];
  manualBalances: ManualBalanceWithValue[];
  manualBalanceByLocation: BalanceByLocation;
  prices: AssetPrices;
}

export interface EditExchange {
  readonly exchange: Exchange;
  readonly newName: Nullable<string>;
}

export interface ExchangeSetupPayload {
  readonly edit: Boolean;
  readonly exchange: ExchangePayload;
}

export interface ExchangePayload {
  readonly name: string;
  readonly newName: Nullable<string>;
  readonly location: SupportedExchange;
  readonly apiKey: Nullable<string>;
  readonly apiSecret: Nullable<string>;
  readonly passphrase: Nullable<string>;
  readonly krakenAccountType: Nullable<KrakenAccountType>;
  readonly binanceMarkets: Nullable<string[]>;
  readonly ftxSubaccount: Nullable<string>;
}

interface XpubPayload {
  readonly xpub: string;
  readonly derivationPath: string;
  readonly xpubType: string;
}

export interface BlockchainAccountPayload extends AccountPayload {
  readonly blockchain: Blockchain;
  readonly xpub?: XpubPayload;
  readonly accounts?: string[];
  readonly modules?: SupportedModules[];
}

export interface AccountPayload {
  readonly address: string;
  readonly label?: string;
  readonly tags: string[];
}

export interface ExchangeBalancePayload {
  readonly location: string;
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

export interface AccountWithBalance extends GeneralAccount, HasBalance {}

interface XpubAccount extends GeneralAccount, XpubPayload {}

interface XpubAccountWithBalance extends XpubAccount, HasBalance {}

export type BlockchainAccount = GeneralAccount | XpubAccount;

export type BlockchainAccountWithBalance =
  | XpubAccountWithBalance
  | AccountWithBalance;

export interface AssetBalance extends Balance {
  readonly asset: string;
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
}

export type AddAccountsPayload = {
  readonly blockchain: Blockchain;
  readonly payload: AccountPayload[];
  readonly modules?: SupportedModules[];
};

interface L2Totals {
  readonly protocol: SupportedL2Protocol;
  readonly usdValue: BigNumber;
  readonly loading: boolean;
}

export interface BlockchainTotal {
  readonly chain: Blockchain;
  readonly l2: L2Totals[];
  readonly usdValue: BigNumber;
  readonly loading: boolean;
}

export type ChainSections = {
  readonly [chain in Blockchain]: Section;
};

export type AssetPrices = {
  [asset: string]: BigNumber;
};

export type AssetPriceResponse = {
  readonly assets: AssetPrices;
  readonly targetAsset: string;
};

export type OracleCachePayload = {
  readonly source: PriceOracles;
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly purgeOld: boolean;
};

type TimedPrices = { [timestamp: string]: BigNumber };

type AssetTimedPrices = { [asset: string]: TimedPrices };

export type HistoricPrices = {
  readonly assets: AssetTimedPrices;
  readonly targetAsset: string;
};

export type HistoricPricePayload = {
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly timestamp: number;
};

export interface AssetPriceInfo extends Balance {
  readonly usdPrice: BigNumber;
}

export interface AssetBreakdown {
  readonly location: string;
  readonly balance: Balance;
  readonly address: string;
}

export interface ERC20Token {
  readonly decimals?: number;
  readonly name?: string;
  readonly symbol?: string;
}

export type ExchangeRateGetter = (currency: string) => BigNumber | undefined;
export type AssetInfoGetter = (
  identifier: string
) => SupportedAsset | undefined;

export type IdentifierForSymbolGetter = (symbol: string) => string | undefined;
export type AssetSymbolGetter = (identifier: string) => string;

export type KrakenAccountType = typeof KRAKEN_ACCOUNT_TYPES[number];
