import type { Blockchain } from '@rotki/common/lib/blockchain';
import type { Balance, HasBalance } from '@rotki/common';
import type { GeneralAccount } from '@rotki/common/lib/account';
import type { Module } from '@/types/modules';

export interface GeneralAccountData {
  readonly address: string;
  readonly label: string | null;
  readonly tags: string[] | null;
}

export interface XpubAccountData {
  readonly xpub: string;
  readonly derivationPath: string | null;
  readonly label: string | null;
  readonly tags: string[] | null;
  readonly addresses: GeneralAccountData[] | null;
}

export interface BtcAccountData {
  readonly standalone: GeneralAccountData[];
  readonly xpubs: XpubAccountData[];
}

export enum XpubKeyType {
  P2TR = 'p2tr',
  XPUB = 'p2pkh',
  YPUB = 'p2sh_p2wpkh',
  ZPUB = 'wpkh',
}

export interface XpubPayload {
  readonly xpub: string;
  readonly blockchain: Blockchain.BTC | Blockchain.BCH;
  readonly derivationPath: string;
  readonly xpubType: XpubKeyType;
}

export interface BasicBlockchainAccountPayload {
  readonly blockchain: string;
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
  readonly tags: string[] | null;
}

export interface ExchangeBalancePayload {
  readonly location: string;
  readonly ignoreCache: boolean;
}

export interface BlockchainBalancePayload {
  readonly blockchain?: string;
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

// todo: flatten balance
export interface AccountWithBalance
  extends GeneralAccount,
  HasBalance,
  Partial<Balance> {
  nativeAsset?: string;
}

interface XpubAccount extends GeneralAccount, XpubPayload {}

// todo: flatten balance
export interface XpubAccountWithBalance
  extends XpubAccount,
  HasBalance,
  Partial<Balance> {}

export interface AccountWithBalanceAndSharedOwnership
  extends AccountWithBalance {
  ownershipPercentage?: string;
}

export type BlockchainAccountWithBalance =
  | XpubAccountWithBalance
  | AccountWithBalanceAndSharedOwnership;

export interface BaseAddAccountsPayload {
  readonly payload: AccountPayload[];
  readonly modules?: Module[];
}

export interface AddAccountsPayload extends BaseAddAccountsPayload {
  readonly blockchain: string;
}

// todo: flatten balance
export interface AssetBreakdown extends Partial<Balance> {
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
