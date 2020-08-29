import { default as BigNumber } from 'bignumber.js';
import { Balance } from '@/model/blockchain-balances';
import { Zero } from '@/utils/bignumbers';

export function assetSum(balances: { [asset: string]: Balance }) {
  return Object.values(balances).reduce((sum, balance) => {
    return sum.plus(balance.usdValue);
  }, Zero);
}

export function toEth(value: BigNumber): BigNumber {
  if (value.isZero()) {
    return value;
  }

  return value.div(new BigNumber('10').pow(18));
}
