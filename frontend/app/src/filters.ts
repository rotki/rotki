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

  const length = address.length;

  if (length <= truncLength * 2 + startPadding) {
    return address;
  }

  return `${address.slice(0, truncLength + startPadding)}...${address.slice(
    length - truncLength,
    length
  )}`;
}
