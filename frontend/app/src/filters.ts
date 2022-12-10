import { type BigNumber } from '@rotki/common';
import { Zero } from '@/utils/bignumbers';

export const truncationPoints: Record<string, number> = {
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
export function truncateAddress(address: string, truncLength = 4): string {
  const startPadding = address.startsWith('0x')
    ? 2
    : address.startsWith('xpub')
    ? 4
    : 0;

  if (address.length <= truncLength * 2 + startPadding) {
    return address;
  }

  return `${address.slice(0, truncLength + startPadding)}...${address!.slice(
    address!.length - truncLength,
    address!.length
  )}`;
}

export function bigNumberSum(value: BigNumber[]): BigNumber {
  return value.reduce(
    (previousValue, currentValue) => previousValue.plus(currentValue),
    Zero
  );
}

export function aggregateTotal(
  balances: any[],
  mainCurrency: string,
  exchangeRate: BigNumber
): BigNumber {
  return balances.reduce((previousValue, currentValue) => {
    if (currentValue.asset === mainCurrency) {
      return previousValue.plus(currentValue.amount);
    }
    return previousValue.plus(currentValue.usdValue.multipliedBy(exchangeRate));
  }, Zero);
}
