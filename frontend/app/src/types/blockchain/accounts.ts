import { z } from 'zod';
import type BigNumber from 'bignumber.js';
import type { Balance } from '@rotki/common';
import type { Module } from '@/types/modules';

export interface AddressData {
  readonly address: string;
}

export interface XpubData {
  readonly xpub: string;
  readonly derivationPath?: string;
}

export interface ValidatorData {
  readonly index: number;
  readonly publicKey: string;
  readonly status: string;
  readonly ownershipPercentage?: string;
  readonly withdrawalAddress?: string;
  readonly activationTimestamp?: number;
  readonly withdrawableTimestamp?: number;
}

export type BlockchainAccountData = AddressData | XpubData | ValidatorData;

export interface BlockchainAccount<T extends BlockchainAccountData = BlockchainAccountData> {
  readonly data: T;
  readonly tags?: string[];
  readonly label?: string;
  readonly chain: string;
  readonly nativeAsset: string;
  readonly groupId?: string;
  readonly groupHeader?: boolean;
  readonly virtual?: boolean;
}

export interface AccountExtraParams {
  readonly chain: string;
  readonly nativeAsset: string;
  readonly groupId?: string;
  readonly groupHeader?: boolean;
}

export interface BlockchainAccountWithBalance<
    T extends BlockchainAccountData = BlockchainAccountData,
> extends BlockchainAccount<T> {
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
  readonly expandable: boolean;
}

export interface BlockchainAccountGroupWithBalance<
    T extends BlockchainAccountData = BlockchainAccountData,
> {
  data: T;
  readonly tags?: string[];
  readonly label?: string;
  readonly amount?: BigNumber;
  readonly usdValue: BigNumber;
  readonly nativeAsset?: string;
  readonly chains: string[];
  readonly expandable: boolean;
}

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

const BasicBlockchainAccount = z.object({
  address: z.string(),
  label: z.string().nullable(),
  tags: z.array(z.string()).nullable(),
});

export type BasicBlockchainAccount = z.infer<typeof BasicBlockchainAccount>;

const BitcoinXpubAccount = z.object({
  xpub: z.string(),
  derivationPath: z.string().nullable(),
  label: z.string().nullable(),
  tags: z.array(z.string()).nullable(),
  addresses: z.array(BasicBlockchainAccount).nullable(),
});

export type BitcoinXpubAccount = z.infer<typeof BitcoinXpubAccount>;

export const BlockchainAccounts = z.array(BasicBlockchainAccount);

export type BlockchainAccounts = z.infer<typeof BlockchainAccounts>;

export const BitcoinAccounts = z.object({
  standalone: z.array(BasicBlockchainAccount),
  xpubs: z.array(BitcoinXpubAccount),
});

export type BitcoinAccounts = z.infer<typeof BitcoinAccounts>;

export enum XpubKeyType {
  P2TR = 'p2tr',
  XPUB = 'p2pkh',
  YPUB = 'p2sh_p2wpkh',
  ZPUB = 'wpkh',
}

export interface XpubPayload {
  readonly xpub: string;
  readonly derivationPath: string;
  readonly xpubType: XpubKeyType;
}

export interface DeleteXpubParams {
  readonly xpub: string;
  readonly derivationPath?: string;
  readonly chain: string;
}

export interface DeleteBlockchainAccountParams {
  readonly chain: string;
  readonly accounts: string[];
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
  readonly tags: string[] | null;
}

export interface XpubAccountPayload extends Omit<AccountPayload, 'address'> {
  readonly xpub: XpubPayload;
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

export interface AddAccountsPayload {
  readonly payload: AccountPayload[];
  readonly modules?: Module[];
}

export interface AssetBreakdown extends Balance {
  readonly location: string;
  readonly address: string;
  readonly tags?: string[];
  readonly detailPath?: string;
}

export interface ERC20Token {
  readonly decimals?: number;
  readonly name?: string;
  readonly symbol?: string;
}
