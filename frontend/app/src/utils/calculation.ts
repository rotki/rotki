import { Balance, BigNumber } from '@rotki/common';
import { get } from '@vueuse/core';
import { useIgnoredAssetsStore } from '@/store/assets';
import { Zero } from '@/utils/bignumbers';

export function assetSum(balances: { [asset: string]: Balance }) {
  const { isAssetIgnored } = useIgnoredAssetsStore();

  return Object.entries(balances).reduce((sum, [asset, balance]) => {
    if (get(isAssetIgnored(asset))) {
      return sum;
    }
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

export function balanceSum(
  sum: Balance,
  { amount, usdValue }: Balance
): Balance {
  return {
    amount: sum.amount.plus(amount),
    usdValue: sum.usdValue.plus(usdValue)
  };
}
