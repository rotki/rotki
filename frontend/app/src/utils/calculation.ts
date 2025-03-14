import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { type Balance, type BigNumber, Zero } from '@rotki/common';

export function assetSum(balances: Record<string, Balance>): BigNumber {
  const { useIsAssetIgnored } = useIgnoredAssetsStore();

  return Object.entries(balances).reduce((sum, [asset, balance]) => {
    if (get(useIsAssetIgnored(asset)))
      return sum;

    return sum.plus(balance.usdValue);
  }, Zero);
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
