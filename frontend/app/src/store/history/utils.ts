import { EthTransaction } from '@/services/history/types';

export const getKey = ({ fromAddress, nonce, txHash }: EthTransaction) =>
  `${txHash}${nonce}${fromAddress}`;
