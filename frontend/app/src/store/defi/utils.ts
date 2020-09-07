import { default as BigNumber } from 'bignumber.js';
import { HasBalance } from '@/services/types-api';
import { Zero } from '@/utils/bignumbers';

export function balanceUsdValueSum(balances: HasBalance[]): BigNumber {
  return balances
    .map(({ balance: { usdValue } }) => usdValue)
    .reduce((sum, value) => sum.plus(value), Zero);
}
