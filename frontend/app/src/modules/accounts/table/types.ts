import type { BlockchainAccountBalance } from '@/types/blockchain/accounts';

export type AccountDataRow<T extends BlockchainAccountBalance = BlockchainAccountBalance> = T & { id: string };
