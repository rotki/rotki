import type { BlockchainAccountData } from '@/types/blockchain/accounts';

function getDataId(group: { data: BlockchainAccountData }): string {
  if (group.data.type === 'address') {
    return group.data.address;
  }
  else if (group.data.type === 'validator') {
    return group.data.publicKey;
  }
  else {
    if (!group.data.derivationPath)
      return group.data.xpub;

    return `${group.data.xpub}#${group.data.derivationPath}`;
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
  else if ('chains' in account && account.chains.length === 1)
    return account.chains[0];
  return undefined;
}
