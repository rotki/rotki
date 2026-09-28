import type {
  AddressData,
  BlockchainAccount,
  BlockchainAccountData,
  BlockchainAccountWithBalance,
  ValidatorData,
  XpubData,
} from '@/modules/accounts/blockchain-accounts';
import { type Brand, make } from 'plainfp/brand';

/**
 * The key of an accounts-table group row: an address, a validator public key, or an xpub on a chain.
 *
 * @remarks
 * Keys the chain exclusions and the `expanded` ids a URL carries, so its format is kept stable.
 */
export type AccountGroupId = Brand<string, 'AccountGroupId'>;

/** The key of one account on one chain. */
export type AccountId = Brand<string, 'AccountId'>;

export function getXpubId(data: Omit<XpubData, 'type'>): string {
  if (!data.derivationPath)
    return data.xpub;

  return `${data.xpub}#${data.derivationPath}`;
}

/** The group of an xpub and every address derived from it on that chain. */
export function getXpubGroupId(data: Omit<XpubData, 'type'>, chain: string): AccountGroupId {
  return make<string, 'AccountGroupId'>(`${getXpubId(data)}#${chain}`);
}

function getDataId(group: { data: BlockchainAccountData }): string {
  if (isAddressAccount(group))
    return group.data.address;
  else if (isValidatorAccount(group))
    return group.data.publicKey;
  else if (isXpubAccount(group))
    return getXpubId(group.data);
  return '';
}

export function getGroupId(group: { data: BlockchainAccountData; chains: string[] }): AccountGroupId {
  if (isXpubAccount(group))
    return getXpubGroupId(group.data, getChain(group) ?? '');

  return make<string, 'AccountGroupId'>(getDataId(group));
}

export function getAccountId(account: { data: BlockchainAccountData; chain: string }): AccountId {
  return make<string, 'AccountId'>(`${getDataId(account)}#${account.chain}`);
}

export function getAccountAddress(account: { data: BlockchainAccountData }): string {
  if (isAddressAccount(account))
    return account.data.address;
  else if (isValidatorAccount(account))
    return account.data.publicKey;
  else if (isXpubAccount(account))
    return account.data.xpub;
  return '';
}

export function getAccountLabel(account: { data: BlockchainAccountData; label?: string }): string {
  if (account.label)
    return account.label;
  else if (isAddressAccount(account))
    return account.data.address;
  else if (isValidatorAccount(account))
    return account.data.index.toString();
  else if (isXpubAccount(account))
    return account.data.xpub;
  return '';
}

function isAddressAccount<T extends { data: BlockchainAccountData }>(account: T): account is T & { data: AddressData } {
  return account.data.type === 'address';
}

export function isValidatorAccount<T extends { data: BlockchainAccountData }>(account: T): account is T & { data: ValidatorData } {
  return account.data.type === 'validator';
}

export function isXpubAccount<T extends { data: BlockchainAccountData }>(account: T): account is T & { data: XpubData } {
  return account.data.type === 'xpub';
}

export function hasAccountAddress(data: BlockchainAccount): data is BlockchainAccount<AddressData> {
  return 'address' in data.data;
}

export function isAccountWithBalanceValidator(
  account: BlockchainAccountWithBalance,
): account is BlockchainAccountWithBalance<ValidatorData> {
  return 'publicKey' in account.data;
}

export function getChain(account: { chain: string } | { chains: string[] }): string | undefined {
  if ('chain' in account)
    return account.chain;
  else if ('chains' in account && account.chains.length > 0)
    return account.chains[0];
  return undefined;
}
