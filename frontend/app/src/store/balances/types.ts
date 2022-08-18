import { Balance, BigNumber, HasBalance, NumericString } from '@rotki/common';
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { z } from 'zod';
import { PriceInformation } from '@/services/assets/types';
import { Section } from '@/store/const';
import { Nullable } from '@/types';
import {
  Exchange,
  KrakenAccountType,
  SupportedExchange
} from '@/types/exchanges';
import { Module } from '@/types/modules';
import { SupportedSubBlockchainProtocol } from '@/types/protocols';
import { PriceOracle } from '@/types/user';

export interface LocationBalance {
  readonly location: string;
  readonly usdValue: BigNumber;
}

export interface BalanceByLocation {
  [location: string]: BigNumber;
}

export interface AssetBalances {
  [asset: string]: Balance;
}

export interface AccountAssetBalances {
  readonly [account: string]: AssetBalances;
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
  readonly blockchain: Blockchain.BTC | Blockchain.BCH;
  readonly derivationPath: string;
  readonly xpubType: XpubKeyType;
}

export interface BasicBlockchainAccountPayload {
  readonly blockchain: Blockchain;
  readonly xpub?: XpubPayload;
  readonly accounts?: string[];
  readonly modules?: Module[];
}

export interface BlockchainAccountPayload
  extends BasicBlockchainAccountPayload,
    AccountPayload {}

export interface AccountPayload {
  readonly address: string;
  readonly label?: string;
  readonly xpub?: XpubPayload;
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

export type AccountWithBalanceAndSharedOwnership = AccountWithBalance & {
  ownershipPercentage?: string;
};

export type BlockchainAccountWithBalance =
  | XpubAccountWithBalance
  | AccountWithBalanceAndSharedOwnership;

export type AddAccountsPayload = {
  readonly blockchain: Blockchain;
  readonly payload: AccountPayload[];
  readonly modules?: Module[];
};

export interface SubBlockchainTotal {
  readonly protocol: SupportedSubBlockchainProtocol;
  readonly usdValue: BigNumber;
  readonly loading: boolean;
}

export interface BlockchainTotal {
  readonly chain: Blockchain;
  readonly children: SubBlockchainTotal[];
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
  readonly detailPath?: string;
}

export interface ERC20Token {
  readonly decimals?: number;
  readonly name?: string;
  readonly symbol?: string;
}

export const NonFungibleBalance = PriceInformation.merge(
  z.object({
    name: z.string().nullable(),
    id: z.string().nonempty(),
    imageUrl: z.string().nullable(),
    isLp: z.boolean().nullish()
  })
);

export type NonFungibleBalance = z.infer<typeof NonFungibleBalance>;

const NonFungibleBalanceArray = z.array(NonFungibleBalance);

export const NonFungibleBalances = z.record(NonFungibleBalanceArray);

export type NonFungibleBalances = z.infer<typeof NonFungibleBalances>;

export const EthNames = z.record(z.string().nullable());

export type EthNames = z.infer<typeof EthNames>;

export const EthNamesEntry = z.object({
  address: z.string(),
  name: z.string()
});

export type EthNamesEntry = z.infer<typeof EthNamesEntry>;

export const EthNamesEntries = z.array(EthNamesEntry);

export type EthNamesEntries = z.infer<typeof EthNamesEntries>;

export const EthAddressBookLocation = z.enum(['global', 'private']);

export const EthNamesPayload = EthNamesEntry.merge(
  z.object({
    location: EthAddressBookLocation
  })
);

export type EthNamesPayload = z.infer<typeof EthNamesPayload>;

export type EthAddressBookLocation = z.infer<typeof EthAddressBookLocation>;

export const BalanceSnapshot = z.object({
  timestamp: z.number(),
  category: z.string(),
  assetIdentifier: z.string(),
  amount: NumericString,
  usdValue: NumericString
});

export type BalanceSnapshot = z.infer<typeof BalanceSnapshot>;

export type BalanceSnapshotPayload = {
  timestamp: number;
  category: string;
  assetIdentifier: string;
  amount: string;
  usdValue: string;
  location: string;
};

export const LocationDataSnapshot = z.object({
  timestamp: z.number(),
  location: z.string(),
  usdValue: NumericString
});

export type LocationDataSnapshot = z.infer<typeof LocationDataSnapshot>;

export type LocationDataSnapshotPayload = {
  timestamp: number;
  location: string;
  usdValue: string;
};

export const Snapshot = z.object({
  balancesSnapshot: z.array(BalanceSnapshot),
  locationDataSnapshot: z.array(LocationDataSnapshot)
});

export type Snapshot = z.infer<typeof Snapshot>;

export type SnapshotPayload = {
  balancesSnapshot: BalanceSnapshotPayload[];
  locationDataSnapshot: LocationDataSnapshotPayload[];
};
