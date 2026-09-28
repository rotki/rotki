import type { AddressAccount, BlockchainAccountWithBalance, ValidatorAccount } from '@/modules/accounts/blockchain-accounts';
import type { BlockchainAssetBalances } from '@/modules/balances/types/blockchain-balances';
import { getAccountGroupId } from '@/modules/accounts/account-utils';
import { type AccountBalancePorts, getAccountBalance } from '@/modules/accounts/core/account-balance';
import { deduplicateTags } from '@/modules/tags/tag-utils';

export function createAccountWithBalance(
  account: AddressAccount | ValidatorAccount,
  chainBalances: BlockchainAssetBalances,
  ports: AccountBalancePorts,
): BlockchainAccountWithBalance {
  const { balance, expansion } = getAccountBalance(account, chainBalances, ports);
  const tags = account.tags ? deduplicateTags(account.tags) : undefined;

  return {
    ...account,
    ...balance,
    expansion,
    groupId: getAccountGroupId(account),
    tags,
    type: 'account',
  };
}
