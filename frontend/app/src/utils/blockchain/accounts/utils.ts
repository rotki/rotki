import type { AddressData, BlockchainAccountData, ValidatorData, XpubData } from '@/types/blockchain/accounts';

export function getXpubId(data: Omit<XpubData, 'type'>): string {
  if (!data.derivationPath)
    return data.xpub;

  return `${data.xpub}#${data.derivationPath}`;
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

export function getGroupId(group: { data: BlockchainAccountData; chains: string[] }): string {
  const main = getDataId(group);
  if (isXpubAccount(group))
    return `${main}#${getChain(group)}`;

  return main;
}

export function getAccountId(account: { data: BlockchainAccountData; chain: string }): string {
  return `${getDataId(account)}#${account.chain}`;
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

export function isAddressAccount<T extends { data: BlockchainAccountData }>(account: T): account is T & { data: AddressData } {
  return account.data.type === 'address';
}

export function isValidatorAccount<T extends { data: BlockchainAccountData }>(account: T): account is T & { data: ValidatorData } {
  return account.data.type === 'validator';
}

export function isXpubAccount<T extends { data: BlockchainAccountData }>(account: T): account is T & { data: XpubData } {
  return account.data.type === 'xpub';
}

export function getChain(account: { chain: string } | { chains: string[] }): string | undefined {
  if ('chain' in account)
    return account.chain;
  else if ('chains' in account && account.chains.length > 0)
    return account.chains[0];
  return undefined;
}
