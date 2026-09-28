import type { BlockchainAccount, BlockchainAccountWithBalance } from '@/modules/accounts/blockchain-accounts';
import type { BlockchainAssetBalances } from '@/modules/balances/types/blockchain-balances';
import { getGroupId } from '@/modules/accounts/account-utils';
import { getAccountBalance } from '@/modules/accounts/core/account-balance';
import { deduplicateTags } from '@/modules/tags/tag-utils';

export function createAccountWithBalance(
  account: BlockchainAccount,
  chainBalances: BlockchainAssetBalances,
  isAssetIgnored: (asset: string) => boolean,
): BlockchainAccountWithBalance {
  const { balance, expansion } = getAccountBalance(account, chainBalances, isAssetIgnored);
  const tags = account.tags ? deduplicateTags(account.tags) : undefined;

  return {
    groupId: getGroupId({ chains: [account.chain], data: account.data }),
    type: 'account',
    ...account,
    ...balance,
    expansion,
    tags,
  } satisfies BlockchainAccountWithBalance;
}
