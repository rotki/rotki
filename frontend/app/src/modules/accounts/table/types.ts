import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';

export type AccountDataRow<T extends BlockchainAccountBalance = BlockchainAccountBalance> = T & { id: string };
