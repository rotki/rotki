import { default as BigNumber } from 'bignumber.js';
import { Zero } from '@/utils/bignumbers';
import { BalanceType, ManualBalanceWithValue } from './services/balances/types';

export function capitalize(string: string): string {
  return string[0].toUpperCase() + string.slice(1);
}

export const truncationPoints: { [breakpoint: string]: number } = {
  xs: 3,
  sm: 6,
  md: 10,
  lg: 20,
  xl: 40
};

/**
 * Truncates blockchain hashes (addresses / txs) retaining `truncLength+2` characters
 * from the beginning and `truncLength` characters from the end of the string.
 * @param address
 * @param [truncLength]
 * @returns truncated address
 */
export function truncateAddress(
  address: string,
  truncLength: number = 4
): string {
  const startPadding = address.startsWith('0x')
    ? 2
    : address.startsWith('xpub')
    ? 4
    : 0;

  if (address.length <= truncLength * 2 + startPadding) {
    return address;
  }

  return (
    address.slice(0, truncLength + startPadding) +
    '...' +
    address!.slice(address!.length - truncLength, address!.length)
  );
}

export function balanceSum(value: BigNumber[]): BigNumber {
  return value.reduce(
    (previousValue, currentValue) => previousValue.plus(currentValue),
    Zero
  );
}

export function aggregateTotal(
  balances: any[],
  mainCurrency: string,
  exchangeRate: BigNumber,
  precision: number
): BigNumber {
  return balances.reduce((previousValue, currentValue) => {
    if (currentValue.asset === mainCurrency) {
      return previousValue
        .plus(currentValue.amount)
        .dp(precision, BigNumber.ROUND_DOWN);
    }
    return previousValue
      .plus(currentValue.usdValue.multipliedBy(exchangeRate))
      .dp(precision, BigNumber.ROUND_DOWN);
  }, Zero);
}

export function aggregateTotalWithLiabilities(
  balances: ManualBalanceWithValue[],
  mainCurrency: string,
  exchangeRate: BigNumber,
  precision: number
): BigNumber {
  return balances.reduce((previousValue, currentValue) => {
    if (currentValue.balanceType === BalanceType.LIABILITY) {
      if (currentValue.asset === mainCurrency) {
        return previousValue
          .minus(currentValue.amount)
          .dp(precision, BigNumber.ROUND_DOWN);
      }
      return previousValue
        .minus(currentValue.usdValue.multipliedBy(exchangeRate))
        .dp(precision, BigNumber.ROUND_DOWN);
    }
    if (currentValue.asset === mainCurrency) {
      return previousValue
        .plus(currentValue.amount)
        .dp(precision, BigNumber.ROUND_DOWN);
    }
    return previousValue
      .plus(currentValue.usdValue.multipliedBy(exchangeRate))
      .dp(precision, BigNumber.ROUND_DOWN);
  }, Zero);
}
