import { default as BigNumber } from 'bignumber.js';
import Vue from 'vue';
import { displayDateFormatter } from '@/data/date_formatter';
import { bigNumberify, Zero } from '@/utils/bignumbers';

export function precision(value: number, precision: number): string {
  return value.toFixed(precision);
}

export function formatDate(value: number, format: string): string {
  return displayDateFormatter.format(new Date(value * 1000), format);
}

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
  exchangeRate: number,
  precision: number
): BigNumber {
  return balances.reduce((previousValue, currentValue) => {
    if (currentValue.asset === mainCurrency) {
      return previousValue
        .plus(currentValue.amount)
        .dp(precision, BigNumber.ROUND_DOWN);
    }
    return previousValue
      .plus(currentValue.usdValue.multipliedBy(bigNumberify(exchangeRate)))
      .dp(precision, BigNumber.ROUND_DOWN);
  }, Zero);
}

export function optional(value?: string): string {
  return value ?? '-';
}

Vue.filter('precision', precision);
Vue.filter('formatDate', formatDate);
Vue.filter('capitalize', capitalize);
Vue.filter('balanceSum', balanceSum);
Vue.filter('truncateAddress', truncateAddress);
Vue.filter('aggregateTotal', aggregateTotal);
Vue.filter('optional', optional);
