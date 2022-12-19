import { type Balance, type HasBalance } from '@rotki/common';
import { type GeneralAccount } from '@rotki/common/lib/account';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type Module } from '@/types/modules';
import { type Section } from '@/types/status';

export enum XpubKeyType {
  P2TR = 'p2tr',
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
  readonly selectedAssets: string[];
}

export interface AccountWithBalance extends GeneralAccount, HasBalance {
  nativeAsset?: string;
}

interface XpubAccount extends GeneralAccount, XpubPayload {}

export interface XpubAccountWithBalance extends XpubAccount, HasBalance {}

export interface AccountWithBalanceAndSharedOwnership
  extends AccountWithBalance {
  ownershipPercentage?: string;
}

export type BlockchainAccountWithBalance =
  | XpubAccountWithBalance
  | AccountWithBalanceAndSharedOwnership;

export interface AddAccountsPayload {
  readonly blockchain: Blockchain;
  readonly payload: AccountPayload[];
  readonly modules?: Module[];
}

export type ChainSections = {
  readonly [chain in Blockchain]: Section;
};

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
