import type { BlockchainAssetBalances } from '@/types/blockchain/balances';
import type { PaginationRequestPayload } from '@/types/common';
import type { Module } from '@/types/modules';
import type { AssetBalance, Balance, BigNumber } from '@rotki/common';
import { z } from 'zod';

export interface AddressData {
  readonly type: 'address';
  readonly address: string;
}

export interface XpubData {
  readonly type: 'xpub';
  readonly xpub: string;
  readonly derivationPath?: string;
}

export interface ValidatorData {
  readonly type: 'validator';
  readonly index: number;
  readonly publicKey: string;
  readonly status: string;
  readonly consolidatedInto?: number;
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

export interface AccountExpansion {
  readonly expansion?: 'accounts' | 'assets';
}

export interface BlockchainAccountWithBalance<T extends BlockchainAccountData = BlockchainAccountData>
  extends BlockchainAccount<T>, AccountExpansion {
  readonly type: 'account';
  readonly category?: string;
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
  readonly includedUsdValue?: BigNumber;
}

export type EthereumValidator = ValidatorData & Balance;

export interface EthereumValidatorRequestPayload extends PaginationRequestPayload<EthereumValidator> {
  readonly index?: string[];
  readonly publicKey?: string[];
  readonly status?: string[];
}

export interface BlockchainAccountGroupWithBalance<T extends BlockchainAccountData = BlockchainAccountData> extends Omit<BlockchainAccount<T>, 'groupHeader' | 'groupId' | 'nativeAsset' | 'chain' | 'virtual'>, AccountExpansion {
  readonly type: 'group';
  readonly category?: string;
  readonly amount?: BigNumber;
  readonly usdValue: BigNumber;
  readonly includedUsdValue?: BigNumber;
  readonly nativeAsset?: string;
  readonly aggregatedAssets?: AssetBalance[];
  readonly chains: string[];
  readonly allChains?: string[];
}

export type BlockchainAccountBalance<
  T extends BlockchainAccountData = BlockchainAccountData,
> = BlockchainAccountWithBalance<T> | BlockchainAccountGroupWithBalance<T>;

export interface BlockchainAccountRequestPayload extends PaginationRequestPayload<BlockchainAccountBalance> {
  readonly address?: string;
  readonly chain?: string[];
  readonly label?: string;
  readonly tags?: string[];
  readonly category?: string;
  readonly excluded?: Record<string, string[]>;
}

export interface BlockchainAccountGroupRequestPayload extends PaginationRequestPayload<BlockchainAccountBalance> {
  readonly groupId: string;
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

export interface BasicBlockchainAccountPayload {
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
  readonly ignoreCache: boolean;
}

export interface BlockchainBalancePayload {
  readonly blockchain?: string | string[];
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

export type Accounts = Record<string, BlockchainAccount[]>;

export type Balances = Record<string, BlockchainAssetBalances>;
