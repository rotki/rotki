import type { BlockchainAccountGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import { isXpubAccount } from '@/modules/accounts/account-utils';

export const AccountDetailsView = {
  ACCOUNTS: 'accounts',
  ADDRESSES: 'addresses',
  ASSETS: 'assets',
  CHAINS: 'chains',
} as const;

export type AccountDetailsView = (typeof AccountDetailsView)[keyof typeof AccountDetailsView];

const views = new Set<string>(Object.values(AccountDetailsView));

export function isAccountDetailsView(value: unknown): value is AccountDetailsView {
  return typeof value === 'string' && views.has(value);
}

/**
 * The tabs the details drawer offers for an account group, in display order.
 *
 * @remarks
 * An xpub with derived addresses only lists them: it holds the chain's native asset alone, which the
 * header already totals. An address tracked on more than one chain shows its assets chain by chain,
 * and lists its account on each chain, where one chain's entry is edited or removed. An address on a
 * single chain has nothing to list beyond its assets.
 */
export function accountDetailsViews(group: BlockchainAccountGroupWithBalance): AccountDetailsView[] {
  if (isXpubAccount(group))
    return group.expansion === 'accounts' ? [AccountDetailsView.ADDRESSES] : [AccountDetailsView.ASSETS];

  return group.chains.length > 1
    ? [AccountDetailsView.ASSETS, AccountDetailsView.CHAINS, AccountDetailsView.ACCOUNTS]
    : [AccountDetailsView.ASSETS];
}
