import { XpubPrefix } from '@/utils/xpub';

export function findAddressKnownPrefix(address: string): string {
  const truncatePrefixExceptions = ['0x', ...Object.values(XpubPrefix)];

  let knownPrefix = '';
  for (const prefix of truncatePrefixExceptions) {
    if (address.startsWith(prefix)) {
      knownPrefix = prefix;
      break;
    }
  }
  return knownPrefix;
}

/**
 * Truncates blockchain hashes (addresses / txs) retaining `truncLength+2` characters
 * from the beginning and `truncLength` characters from the end of the string.
 * @param address
 * @param [truncLength]
 * @returns truncated address
 */
export function truncateAddress(address: string, truncLength = 4): string {
  const knownPrefix = findAddressKnownPrefix(address);
  const startPadding = knownPrefix.length;

  const length = address.length;

  if (length <= truncLength * 2 + startPadding + 3)
    return address;

  return `${address.slice(0, truncLength + startPadding)}...${address.slice(length - truncLength, length)}`;
}
