import { Balance, BigNumber, HasBalance } from '@rotki/common';
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { SupportedAsset } from '@rotki/common/lib/data';
import { Eth2Validators } from '@rotki/common/lib/staking/eth2';
import { z } from 'zod';
import { PriceInformation } from '@/services/assets/types';
import {
  BlockchainAssetBalances,
  BtcBalances,
  ManualBalanceWithValue
} from '@/services/balances/types';
import { BtcAccountData, GeneralAccountData } from '@/services/types-api';
import { Section } from '@/store/const';
import { Nullable } from '@/types';
import {
  Exchange,
  ExchangeData,
  KrakenAccountType,
  SupportedExchange
} from '@/types/exchanges';
import { Module } from '@/types/modules';
import { SupportedL2Protocol } from '@/types/protocols';
import { ExchangeRates, PriceOracle } from '@/types/user';

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
  eth2Validators: Eth2Validators;
  loopringBalances: AccountAssetBalances;
  eth: BlockchainAssetBalances;
  eth2: BlockchainAssetBalances;
  btc: BtcBalances;
  ksm: BlockchainAssetBalances;
  dot: BlockchainAssetBalances;
  avax: BlockchainAssetBalances;
  totals: AssetBalances;
  liabilities: AssetBalances;
  usdToFiatExchangeRates: ExchangeRates;
  connectedExchanges: Exchange[];
  exchangeBalances: ExchangeData;
  ethAccounts: GeneralAccountData[];
  btcAccounts: BtcAccountData;
  ksmAccounts: GeneralAccountData[];
  dotAccounts: GeneralAccountData[];
  avaxAccounts: GeneralAccountData[];
  supportedAssets: SupportedAsset[];
  manualBalances: ManualBalanceWithValue[];
  manualLiabilities: ManualBalanceWithValue[];
  manualBalanceByLocation: BalanceByLocation;
  prices: AssetPrices;
  nonFungibleBalances: NonFungibleBalances;
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

export enum XpubKeyType {
  XPUB = 'p2pkh',
  YPUB = 'p2sh_p2wpkh',
  ZPUB = 'wpkh'
}

export interface XpubPayload {
  readonly xpub: string;
  readonly derivationPath: string;
  readonly xpubType: XpubKeyType;
}

export interface BlockchainAccountPayload extends AccountPayload {
  readonly blockchain: Blockchain;
  readonly xpub?: XpubPayload;
  readonly accounts?: string[];
  readonly modules?: Module[];
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
  readonly ignoreErrors: boolean;
}

export interface FetchPricePayload {
  readonly ignoreCache: boolean;
  readonly selectedAsset?: string;
}

export interface AccountWithBalance extends GeneralAccount, HasBalance {}

interface XpubAccount extends GeneralAccount, XpubPayload {}

export interface XpubAccountWithBalance extends XpubAccount, HasBalance {}

export type BlockchainAccount = GeneralAccount | XpubAccount;

export type BlockchainAccountWithBalance =
  | XpubAccountWithBalance
  | (AccountWithBalance & { ownershipPercentage?: string });

export type AddAccountsPayload = {
  readonly blockchain: Blockchain;
  readonly payload: AccountPayload[];
  readonly modules?: Module[];
};

export interface L2Totals {
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
  readonly source: PriceOracle;
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
  readonly tags: string[] | null;
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

export const NonFungibleBalance = PriceInformation.merge(
  z.object({
    name: z.string().nullable(),
    id: z.string().nonempty(),
    imageUrl: z.string().nullable()
  })
);

export type NonFungibleBalance = z.infer<typeof NonFungibleBalance>;

const NonFungibleBalanceArray = z.array(NonFungibleBalance);

export const NonFungibleBalances = z.record(NonFungibleBalanceArray);

export type NonFungibleBalances = z.infer<typeof NonFungibleBalances>;
