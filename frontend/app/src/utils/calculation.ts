import type { ProtocolBalances } from '@/types/blockchain/balances';
import { type Balance, type BigNumber, Zero } from '@rotki/common';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';

export function assetSum(balances: Record<string, ProtocolBalances>): BigNumber {
  const { useIsAssetIgnored } = useIgnoredAssetsStore();

  return Object.entries(balances).reduce((sum, [asset, protocols]) => {
    if (get(useIsAssetIgnored(asset)))
      return sum;

    return sum.plus(Object.entries(protocols).reduce((previousValue, [_protocol, balance]) => previousValue.plus(balance.value), Zero));
  }, Zero);
}

export function exchangeAssetSum(balances: Record<string, Balance>): BigNumber {
  const { useIsAssetIgnored } = useIgnoredAssetsStore();

  return Object.entries(balances).reduce((sum, [asset, balance]) => {
    if (get(useIsAssetIgnored(asset)))
      return sum;

    return sum.plus(balance.value);
  }, Zero);
}

export function balanceSum(sum: Balance, { amount, value }: Balance): Balance {
  return {
    amount: sum.amount.plus(amount),
    value: sum.value.plus(value),
  };
}

export function perProtocolBalanceSum(sum: Balance, balances: ProtocolBalances): Balance {
  return Object.values(balances)
    .reduce((previousValue, currentValue) => balanceSum(previousValue, currentValue), sum);
}

export function calculatePercentage(value: BigNumber, divider: BigNumber): string {
  const percentage = divider.isZero() ? 0 : value.div(divider).multipliedBy(100);
  return percentage.toFixed(2);
}

export function bigNumberSum(value: BigNumber[]): BigNumber {
  return value.reduce((previousValue, currentValue) => previousValue.plus(currentValue), Zero);
}
