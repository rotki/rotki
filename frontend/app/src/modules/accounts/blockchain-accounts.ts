import type { Balance, BigNumber } from '@rotki/common';
import type { AccountGroupId } from '@/modules/accounts/account-utils';
import type { BlockchainAssetBalances } from '@/modules/balances/types/blockchain-balances';
import type { AccountCategory } from '@/modules/core/api/types/chains';
import type { PaginationRequestPayload } from '@/modules/core/common/common-types';
import type { Module } from '@/modules/core/common/modules';
import { z } from 'zod';

/** What identifies an account: an address, an xpub, or a beacon chain validator. */
export const AccountKind = {
  ADDRESS: 'address',
  VALIDATOR: 'validator',
  XPUB: 'xpub',
} as const;

export type AccountKind = (typeof AccountKind)[keyof typeof AccountKind];

export interface XpubKey {
  readonly xpub: string;
  readonly derivationPath?: string;
}

export interface ValidatorDetails {
  readonly index: number;
  readonly publicKey: string;
  readonly status: string;
  readonly consolidatedInto?: number;
  readonly ownershipPercentage?: string;
  readonly withdrawalAddress?: string;
  readonly activationTimestamp?: number;
  readonly withdrawableTimestamp?: number;
}

export interface AddressIdentity {
  readonly kind: typeof AccountKind.ADDRESS;
  readonly address: string;
}

export interface XpubIdentity extends XpubKey {
  readonly kind: typeof AccountKind.XPUB;
}

export interface ValidatorIdentity extends ValidatorDetails {
  readonly kind: typeof AccountKind.VALIDATOR;
}

/** The identity part shared by stored accounts and table rows, discriminated by `kind`. */
export type AccountIdentity = AddressIdentity | XpubIdentity | ValidatorIdentity;

interface AccountMeta {
  readonly label?: string;
  readonly tags?: string[];
}

interface OnChain {
  readonly chain: string;
}

export interface AddressAccount extends AddressIdentity, AccountMeta, OnChain {
  /** The xpub this address was derived from; absent for an address added on its own. */
  readonly xpubParent?: XpubKey;
}

export interface XpubAccount extends XpubIdentity, AccountMeta, OnChain {}

export interface ValidatorAccount extends ValidatorIdentity, AccountMeta, OnChain {}

/** An account as tracked in the store, one per chain. */
export type BlockchainAccount = AddressAccount | XpubAccount | ValidatorAccount;

interface RowBalance {
  readonly value: BigNumber;
  /** The value left once the chains excluded from the row are taken out. */
  readonly includedValue?: BigNumber;
  readonly expansion?: 'accounts' | 'assets';
}

/**
 * An account with its balance. An xpub is never a row of its own; it is shown as an
 * {@link XpubGroupWithBalance} over its derived addresses.
 */
export type BlockchainAccountWithBalance<A extends AddressAccount | ValidatorAccount = AddressAccount | ValidatorAccount> = A & RowBalance & {
  readonly type: 'account';
  readonly amount: BigNumber;
  readonly groupId: AccountGroupId;
};

interface GroupRow extends AccountMeta, RowBalance {
  readonly type: 'group';
  readonly category: AccountCategory;
  readonly chains: string[];
  /** Every chain the group spans, kept when a filter narrows `chains`. */
  readonly allChains?: string[];
}

/** One address across every chain it is tracked on. */
export interface AddressGroupWithBalance extends AddressIdentity, GroupRow {}

/** One xpub, summing the addresses derived from it. */
export interface XpubGroupWithBalance extends XpubIdentity, GroupRow {
  readonly amount: BigNumber;
  readonly nativeAsset: string;
}

export type BlockchainAccountGroupWithBalance = AddressGroupWithBalance | XpubGroupWithBalance;

export type BlockchainAccountBalance = BlockchainAccountWithBalance | BlockchainAccountGroupWithBalance;

export type EthereumValidator = ValidatorDetails & Balance;

export interface EthereumValidatorRequestPayload extends PaginationRequestPayload<EthereumValidator> {
  readonly index?: string[];
  readonly publicKey?: string[];
  readonly status?: string[];
}

export interface BlockchainAccountRequestPayload extends PaginationRequestPayload<BlockchainAccountBalance> {
  /** Picked account addresses; a row matches when it is one of them. */
  readonly addresses?: string[];
  readonly chain?: string[];
  readonly tags?: string[];
  readonly category?: string;
  readonly excluded?: Record<string, string[]>;
}

export interface BlockchainAccountGroupRequestPayload extends PaginationRequestPayload<BlockchainAccountBalance> {
  readonly groupId: AccountGroupId;
}

export interface GeneralAccountData {
  readonly address: string;
  readonly label: string | null;
  readonly tags: string[] | null;
}

const BasicBlockchainAccount = z.object({
  address: z.string(),
  label: z.string().nullable(),
  tags: z.array(z.string()).nullable(),
});

export type BasicBlockchainAccount = z.infer<typeof BasicBlockchainAccount>;

const BitcoinXpubAccount = z.object({
  addresses: z.array(BasicBlockchainAccount).nullable(),
  derivationPath: z.string().nullable(),
  label: z.string().nullable(),
  tags: z.array(z.string()).nullable(),
  xpub: z.string(),
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

interface BasicBlockchainAccountPayload {
  readonly blockchain: string;
  readonly xpub?: XpubPayload;
  readonly accounts?: string[];
  readonly modules?: Module[];
}

export interface BlockchainAccountPayload extends BasicBlockchainAccountPayload, AccountPayload {}

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
  readonly ignoreCache?: boolean;
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

export type Accounts = Record<string, BlockchainAccount[]>;

export type Balances = Record<string, BlockchainAssetBalances>;
