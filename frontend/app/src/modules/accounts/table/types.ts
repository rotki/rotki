import type { AccountGroupId, AccountId } from '@/modules/accounts/account-utils';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';

export type AccountDataRow<T extends BlockchainAccountBalance = BlockchainAccountBalance> = T & { id: AccountId | AccountGroupId };
