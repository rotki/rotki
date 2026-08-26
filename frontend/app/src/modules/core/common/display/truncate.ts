import { XpubPrefix } from '@/modules/accounts/xpub';

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
 * Truncates a blockchain hash (address or transaction), keeping `truncLength + 2` characters from
 * the start and `truncLength` from the end.
 *
 * @param address - the hash to truncate; a known prefix such as `0x` is kept on top of the budget
 * @param truncLength - characters to keep from the end, defaulting to 4
 */
export function truncateAddress(address: string, truncLength = 4): string {
  const knownPrefix = findAddressKnownPrefix(address);
  const startPadding = knownPrefix.length;

  const length = address.length;

  if (length <= truncLength * 2 + startPadding + 3)
    return address;

  return `${address.slice(0, truncLength + startPadding)}...${address.slice(length - truncLength, length)}`;
}
