import type {
  Accounts,
  Balances,
  BlockchainAccount,
  BlockchainAccountBalance,
  EthereumValidator,
  XpubKey,
} from '@/modules/accounts/blockchain-accounts';
import type { AccountCategory } from '@/modules/core/api/types/chains';
import { omit } from 'es-toolkit';
import { getAccountAddress, getXpubGroupId, isAddressAccount, isXpubAccount } from '@/modules/accounts/account-utils';
import { isBlockchain } from '@/modules/core/common/chains';

export type ShowConfirmationParams = {
  type: 'account';
  data: BlockchainAccountBalance;
} | {
  type: 'validator';
  data: EthereumValidator[];
};

/** How a confirmed delete reaches the backend. */
export const DeletionKind = {
  EVERYWHERE: 'everywhere',
  ON_CHAIN: 'on-chain',
  ON_CHAINS: 'on-chains',
  VALIDATORS: 'validators',
  XPUB: 'xpub',
} as const;

export type DeletionKind = (typeof DeletionKind)[keyof typeof DeletionKind];

/**
 * What confirming a delete removes. It is decided once, so the confirmation names exactly what the
 * delete then sends.
 */
export type AccountDeletion =
  | { readonly kind: typeof DeletionKind.VALIDATORS; readonly validators: EthereumValidator[] }
  | { readonly kind: typeof DeletionKind.XPUB; readonly chain: string; readonly key: XpubKey }
  | { readonly kind: typeof DeletionKind.ON_CHAIN; readonly address: string; readonly chain: string }
  | { readonly kind: typeof DeletionKind.ON_CHAINS; readonly address: string; readonly chains: string[] }
  | { readonly kind: typeof DeletionKind.EVERYWHERE; readonly address: string; readonly category: AccountCategory; readonly chains: string[] };

const RemovedKind = {
  ACCOUNTS: 'accounts',
  XPUB: 'xpub',
} as const;

/**
 * What left the backend, for the store to drop the same.
 *
 * @remarks
 * An xpub is matched by its whole key, since the backend tells two derivation paths of one xpub
 * apart. `identities` are addresses, or public keys for validators.
 */
export type RemovedAccounts =
  | { readonly kind: typeof RemovedKind.ACCOUNTS; readonly chains: readonly string[]; readonly identities: readonly string[] }
  | { readonly kind: typeof RemovedKind.XPUB; readonly chain: string; readonly key: XpubKey };

export function removedAccounts(identities: readonly string[], chains: readonly string[]): RemovedAccounts {
  return { chains, identities, kind: RemovedKind.ACCOUNTS };
}

export function removedXpub(key: XpubKey, chain: string): RemovedAccounts {
  return { chain, key, kind: RemovedKind.XPUB };
}

export function removedChains(removed: RemovedAccounts): readonly string[] {
  return removed.kind === RemovedKind.ACCOUNTS ? removed.chains : [removed.chain];
}

/**
 * Decides what a confirmed delete of the row removes.
 *
 * @remarks
 * What the user is deleting depends on how the row was displayed, not only on what it holds. A
 * group is deleted per chain when it shows exactly one, and agnostically (every chain of its
 * category, including ones not on screen) when `chains` covers all of `allChains`. Between those, a
 * group showing a subset deletes only the chains it shows, or the user loses chains they could not
 * see. Virtual chains are left out throughout, since the backend has no such chain to delete from.
 */
export function planDeletion(params: ShowConfirmationParams): AccountDeletion {
  if (params.type === 'validator')
    return { kind: DeletionKind.VALIDATORS, validators: params.data };

  const account = params.data;
  if (account.type === 'account')
    return { address: getAccountAddress(account), chain: account.chain, kind: DeletionKind.ON_CHAIN };

  if (isXpubAccount(account))
    return { chain: account.chains[0], key: { derivationPath: account.derivationPath, xpub: account.xpub }, kind: DeletionKind.XPUB };

  const address = getAccountAddress(account);
  const chains = account.chains.filter(isBlockchain);
  const allChains = account.allChains?.filter(isBlockchain);

  if (chains.length === 1)
    return { address, chain: chains[0], kind: DeletionKind.ON_CHAIN };

  if (allChains && allChains.length > chains.length)
    return { address, chains, kind: DeletionKind.ON_CHAINS };

  return { address, category: account.category, chains, kind: DeletionKind.EVERYWHERE };
}

function isRemoved(account: BlockchainAccount, removed: RemovedAccounts, chain: string): boolean {
  if (removed.kind === RemovedKind.ACCOUNTS)
    return removed.identities.includes(getAccountAddress(account));

  const removedGroupId = getXpubGroupId(removed.key, chain);
  if (isXpubAccount(account))
    return getXpubGroupId(account, chain) === removedGroupId;

  return isAddressAccount(account) && !!account.xpubParent && getXpubGroupId(account.xpubParent, chain) === removedGroupId;
}

/** The accounts and balances left once `removed` is dropped from them. Neither input is modified. */
export function withoutRemoved(
  state: { accounts: Accounts; balances: Balances },
  removed: RemovedAccounts,
): { accounts: Accounts; balances: Balances } {
  const accounts = { ...state.accounts };
  const balances = { ...state.balances };
  const identities = removed.kind === RemovedKind.ACCOUNTS ? removed.identities : [];

  for (const chain of removedChains(removed)) {
    const chainAccounts = accounts[chain] ?? [];
    const gone = chainAccounts.filter(account => isRemoved(account, removed, chain));
    const goneAddresses = [
      ...identities,
      ...gone.filter(isAddressAccount).map(account => account.address),
    ];

    if (accounts[chain])
      accounts[chain] = chainAccounts.filter(account => !gone.includes(account));

    if (balances[chain])
      balances[chain] = omit(balances[chain], goneAddresses);
  }

  return { accounts, balances };
}
