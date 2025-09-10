import type { BlockchainAccountData, XpubData } from '@/types/blockchain/accounts';

export function getXpubId(data: Omit<XpubData, 'type'>): string {
  if (!data.derivationPath)
    return data.xpub;

  return `${data.xpub}#${data.derivationPath}`;
}

function getDataId(group: { data: BlockchainAccountData }): string {
  const data = group.data;
  if (data.type === 'address') {
    return data.address;
  }
  else if (data.type === 'validator') {
    return data.publicKey;
  }
  else {
    return getXpubId(data);
  }
}

export function getGroupId(group: { data: BlockchainAccountData; chains: string[] }): string {
  const main = getDataId(group);
  if (group.data.type === 'xpub')
    return `${main}#${getChain(group)}`;

  return main;
}

export function getAccountId(account: { data: BlockchainAccountData; chain: string }): string {
  return `${getDataId(account)}#${account.chain}`;
}

export function getAccountAddress(account: { data: BlockchainAccountData }): string {
  if (account.data.type === 'address')
    return account.data.address;
  else if (account.data.type === 'validator')
    return account.data.publicKey;
  else return account.data.xpub;
}

export function getAccountLabel(account: { data: BlockchainAccountData; label?: string }): string {
  if (account.label)
    return account.label;
  else if (account.data.type === 'address')
    return account.data.address;
  else if (account.data.type === 'validator')
    return account.data.index.toString();
  else if (account.data.type === 'xpub')
    return account.data.xpub;
  return '';
}

export function getChain(account: { chain: string } | { chains: string[] }): string | undefined {
  if ('chain' in account)
    return account.chain;
  else if ('chains' in account && account.chains.length > 0)
    return account.chains[0];
  return undefined;
}
