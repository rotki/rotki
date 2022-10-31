import { Balance, BigNumber } from '@rotki/common';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { Zero } from '@/utils/bignumbers';

export const assetSum = (balances: { [asset: string]: Balance }) => {
  const { isAssetIgnored } = useIgnoredAssetsStore();

  return Object.entries(balances).reduce((sum, [asset, balance]) => {
    if (get(isAssetIgnored(asset))) {
      return sum;
    }
    return sum.plus(balance.usdValue);
  }, Zero);
};

export enum Unit {
  GWEI,
  ETH
}

export const toUnit = (value: BigNumber, unit: Unit = Unit.ETH): BigNumber => {
  if (value.isZero()) {
    return value;
  }

  const pow = unit === Unit.ETH ? 18 : 9;
  return value.div(new BigNumber('10').pow(pow));
};

export const balanceSum = (
  sum: Balance,
  { amount, usdValue }: Balance
): Balance => ({
  amount: sum.amount.plus(amount),
  usdValue: sum.usdValue.plus(usdValue)
});

export const calculatePercentage = (value: BigNumber, divider: BigNumber) => {
  const percentage = divider.isZero()
    ? 0
    : value.div(divider).multipliedBy(100);
  return percentage.toFixed(2);
};
