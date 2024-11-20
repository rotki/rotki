import type { Balance, BigNumber } from '@rotki/common';

export function assetSum(balances: Record<string, Balance>): BigNumber {
  const { isAssetIgnored } = useIgnoredAssetsStore();

  return Object.entries(balances).reduce((sum, [asset, balance]) => {
    if (get(isAssetIgnored(asset)))
      return sum;

    return sum.plus(balance.usdValue);
  }, Zero);
}

export enum Unit {
  GWEI,
  ETH,
}

export function toUnit(value: BigNumber, unit: Unit = Unit.ETH): BigNumber {
  if (value.isZero())
    return value;

  const pow = unit === Unit.ETH ? 18 : 9;
  return value.div(bigNumberify('10').pow(pow));
}

export function balanceSum(sum: Balance, { amount, usdValue }: Balance): Balance {
  return {
    amount: sum.amount.plus(amount),
    usdValue: sum.usdValue.plus(usdValue),
  };
}

export function calculatePercentage(value: BigNumber, divider: BigNumber): string {
  const percentage = divider.isZero() ? 0 : value.div(divider).multipliedBy(100);
  return percentage.toFixed(2);
}

export function bigNumberSum(value: BigNumber[]): BigNumber {
  return value.reduce((previousValue, currentValue) => previousValue.plus(currentValue), Zero);
}

export function aggregateTotal(balances: any[], mainCurrency: string, exchangeRate: BigNumber): BigNumber {
  return balances.reduce((previousValue, currentValue) => {
    if (currentValue.asset === mainCurrency)
      return previousValue.plus(currentValue.amount);

    return previousValue.plus(currentValue.usdValue.multipliedBy(exchangeRate));
  }, Zero);
}
