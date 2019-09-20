import { AssetBalance } from '@/model/blockchain-balances';
import { Zero } from '@/utils/bignumbers';

export function assetSum(balances: { [asset: string]: AssetBalance }) {
  return Object.values(balances).reduce((sum, balance) => {
    return sum.plus(balance.usdValue);
  }, Zero);
}
