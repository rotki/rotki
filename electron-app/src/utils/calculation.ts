import { Balance } from '@/model/blockchain-balances';
import { Zero } from '@/utils/bignumbers';

export function assetSum(balances: { [asset: string]: Balance }) {
  return Object.values(balances).reduce((sum, balance) => {
    return sum.plus(balance.usdValue);
  }, Zero);
}
