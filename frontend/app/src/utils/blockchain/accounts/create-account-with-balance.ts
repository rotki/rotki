import type { BlockchainAccount, BlockchainAccountWithBalance } from '@/modules/accounts/blockchain-accounts';
import type { BlockchainAssetBalances } from '@/modules/balances/types/blockchain-balances';
import { getAccountBalance } from '@/utils/blockchain/accounts/index';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { deduplicateTags } from '@/utils/tags';

export function createAccountWithBalance(
  account: BlockchainAccount,
  chainBalances: BlockchainAssetBalances,
  isAssetIgnored: (asset: string) => boolean,
): BlockchainAccountWithBalance {
  const { balance, expansion } = getAccountBalance(account, chainBalances, isAssetIgnored);
  const address = getAccountAddress(account);
  const tags = account.tags ? deduplicateTags(account.tags) : undefined;

  return {
    groupId: address,
    type: 'account',
    ...account,
    ...balance,
    expansion,
    tags,
  } satisfies BlockchainAccountWithBalance;
}
