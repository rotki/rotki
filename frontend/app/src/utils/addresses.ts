import { uniqueStrings } from '@/utils/data';
import type { AddressIndexed } from '@rotki/common';

export function getProtocolAddresses(balances: AddressIndexed<any>, history: AddressIndexed<any> | string[]): string[] {
  return [...Object.keys(balances), ...(Array.isArray(history) ? history : Object.keys(history))].filter(uniqueStrings);
}
