import type { BlockchainAccount, BlockchainAccountWithBalance } from '@/types/blockchain/accounts';
import type { BlockchainAssetBalances } from '@/types/blockchain/balances';
import { getAccountBalance } from '@/utils/blockchain/accounts/index';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';

export function createAccountWithBalance(
  account: BlockchainAccount,
  chainBalances: BlockchainAssetBalances,
): BlockchainAccountWithBalance {
  const { balance, expansion } = getAccountBalance(account, chainBalances);
  const address = getAccountAddress(account);

  return {
    groupId: address,
    type: 'account',
    ...account,
    ...balance,
    expansion,
  } satisfies BlockchainAccountWithBalance;
}
