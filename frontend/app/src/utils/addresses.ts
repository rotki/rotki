import { type AddressIndexed } from '@rotki/common';
import { type AddressEntries } from '@/types/addresses';

export function filterAddresses<T>(
  entries: AddressEntries<T>,
  addresses: string[],
  item: (item: T) => void
): void {
  for (const address in entries) {
    if (addresses.length > 0 && !addresses.includes(address)) {
      continue;
    }
    item(entries[address]);
  }
}

export const getProtocolAddresses = (
  balances: AddressIndexed<any>,
  history: AddressIndexed<any> | string[]
): string[] =>
  [
    ...Object.keys(balances),
    ...(Array.isArray(history) ? history : Object.keys(history))
  ].filter(uniqueStrings);
