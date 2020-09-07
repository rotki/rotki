import { default as BigNumber } from 'bignumber.js';
import { Balance } from '@/services/types-api';
import { Zero } from '@/utils/bignumbers';

export function assetSum(balances: { [asset: string]: Balance }) {
  return Object.values(balances).reduce((sum, balance) => {
    return sum.plus(balance.usdValue);
  }, Zero);
}

export enum Unit {
  GWEI,
  ETH
}

export function toUnit(value: BigNumber, unit: Unit = Unit.ETH): BigNumber {
  if (value.isZero()) {
    return value;
  }

  const pow = unit === Unit.ETH ? 18 : 9;
  return value.div(new BigNumber('10').pow(pow));
}
