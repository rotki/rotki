import type { BigNumber } from '@rotki/common';

type Balance = ({ usdValue: BigNumber } | { value: BigNumber }) & { amount: BigNumber };

export function assetSum(balances: Record<string, Balance>): BigNumber {
  const { isAssetIgnored } = useIgnoredAssetsStore();

  return Object.entries(balances).reduce((sum, [asset, balance]) => {
    if (get(isAssetIgnored(asset)))
      return sum;

    return sum.plus(`usdValue` in balance ? balance.usdValue : balance.value);
  }, Zero);
}

export function balanceSum<T extends Balance>(sum: T, balance: T): T {
  if (`usdValue` in sum && `usdValue` in balance) {
    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
    return {
      amount: sum.amount.plus(balance.amount),
      usdValue: sum.usdValue.plus(balance.usdValue),
    } as T;
  }
  else if (`value` in sum && `value` in balance) {
    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
    return {
      amount: sum.amount.plus(balance.amount),
      value: sum.value.plus(balance.value),
    } as T;
  }
  else {
    throw new Error('Invalid balance');
  }
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
