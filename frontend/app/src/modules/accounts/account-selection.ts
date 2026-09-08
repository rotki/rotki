import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { getTextToken } from '@rotki/common';
import { uniqBy } from 'es-toolkit';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { createAccount } from '@/modules/accounts/create-account';

type AccountWithAddressData = BlockchainAccount<AddressData>;

/** How the caller wants the offered accounts narrowed. */
export interface AccountSelectionOptions {
  /** Offer only these chains; empty offers every chain. */
  readonly chains?: string[];
  /** Collapse an address tracked on several chains into one entry. */
  readonly unique?: boolean;
  /** Offer an extra all-chains entry for an address tracked on more than one. */
  readonly multichain?: boolean;
}

/**
 * Narrows the tracked accounts to the ones the selector should offer.
 *
 * @remarks
 * With `multichain`, an address tracked on more than one chain gains an extra entry standing for
 * all of them, alongside its per-chain entries. That entry is synthesized here rather than being
 * a real account, so the result is always a new array: appending to the caller's would grow the
 * list again on every pass.
 *
 * @param accounts - every tracked account that has an address
 * @param options - how to narrow them
 * @returns the accounts to offer, in the order they were tracked
 */
export function selectableAccounts(
  accounts: AccountWithAddressData[],
  options: AccountSelectionOptions = {},
): AccountWithAddressData[] {
  const { chains = [], multichain = false, unique = false } = options;

  const byChain = chains.length === 0
    ? accounts
    : accounts.filter(({ chain }) => chain === 'ALL' || chains.includes(chain));

  const selected = unique
    ? uniqBy(byChain, account => getAccountAddress(account))
    : byChain;

  return multichain ? [...selected, ...allChainsEntries(selected)] : [...selected];
}

/** An all-chains entry for each address that appears on more than one chain. */
function allChainsEntries(accounts: AccountWithAddressData[]): AccountWithAddressData[] {
  const perAddress = new Map<string, number>();
  for (const account of accounts) {
    const address = getAccountAddress(account);
    perAddress.set(address, (perAddress.get(address) ?? 0) + 1);
  }

  return [...perAddress]
    .filter(([, count]) => count > 1)
    .map(([address]) => createAccount({ address, label: null, tags: null }, { chain: 'ALL', nativeAsset: '' }));
}

/**
 * Whether an account matches what the user typed, which is the address, the name it resolves to,
 * or any of its tags.
 *
 * @param account - the account being offered
 * @param query - what the user typed
 * @param resolveName - the tracked or ENS name for an address, absent when it has none
 * @returns whether the account should stay in the list
 */
export function matchesAccountQuery(
  account: BlockchainAccount,
  query: string,
  resolveName: (account: BlockchainAccount) => string | undefined,
): boolean {
  const token = getTextToken(query);
  const address = getTextToken(getAccountAddress(account));
  const name = getTextToken(resolveName(account) ?? '');

  if (address.includes(token) || name.includes(token))
    return true;

  return account.tags
    ? account.tags.map(tag => getTextToken(tag)).join(' ').includes(token)
    : false;
}
